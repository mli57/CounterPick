"""
FastAPI server

How to run: 
    uvicorn src.api.main:app --reload
"""
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.predict import load_model, predict_matchup


DB_PATH = "lol_draft.db"
MODEL_PATH = "models/model.pkl"

state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: load model and db into dict
    state["model"] = load_model(MODEL_PATH)
    state["conn"] = sqlite3.connect(DB_PATH, check_same_thread=False)
    yield

    #shutdown: runs when server stops
    state["conn"].close()

app = FastAPI(title="CounterPick API", lifespan=lifespan) # wire lifespan into app instance

app.add_middleware( # add CORS so frontend can talk to app
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"], # tells browser to not block react frontend
    allow_headers=["*"],
)


# get champion name and roles from db
@app.get("/champions")
def get_champions():
    query = """
    SELECT champion_name, majority_role FROM champion_meta
    JOIN champion_role_majority USING (champion_id)
    WHERE patch = (SELECT MAX(patch) FROM champion_role_majority)
    ORDER BY champion_name
    """

    champ_list = state["conn"].execute(query).fetchall()
    champions: dict[str, list[str]] = {}
    for name, roles in champ_list:
        champions.setdefault(name, []).append(roles)

    result = []
    for name, roles in champions.items():
        result.append({"name": name, "roles": roles})
    return result
    


# define requests
class PredictRequest(BaseModel):
    champion: str
    opponent: str
    role: str

# post model prediction results to frontend
@app.post("/predict")
def predict(req: PredictRequest):
    try:
        result = predict_matchup(
            state["conn"],
            state["model"],
            req.champion,
            req.opponent,
            req.role.upper(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return result