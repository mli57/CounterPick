"""
FastAPI server

How to run: 
    uvicorn src.api.main:app --reload
"""
import os
import requests
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.predict import load_model, predict_matchup


DB_PATH = "test.db"
MODEL_PATH = "models/model.pkl"

state = {}

def riot_get(url):
    response = requests.get(url, headers={"X-Riot-Token": state["api_key"]})
    response.raise_for_status()
    return response.json()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: load model and db into dict
    state["model"] = load_model(MODEL_PATH)
    state["conn"] = sqlite3.connect(DB_PATH, check_same_thread=False)
    state["api_key"] = os.environ.get("RIOT_API_KEY", "").strip()
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
    

ROLE_MAP = {
    "TOP": "TOP",
    "JNG": "JUNGLE",
    "MID": "MIDDLE",
    "ADC": "BOTTOM",
    "SUP": "UTILITY",
}

# define requests
class PredictRequest(BaseModel):
    champion: str
    opponent: str
    role: str

# post model prediction results to frontend
@app.post("/predict")
def predict(req: PredictRequest):
    role = ROLE_MAP.get(req.role.upper())
    if role is None:
        raise HTTPException(status_code=400, detail=f"Unknown role: {req.role}")
    try:
        result = predict_matchup(
            state["conn"],
            state["model"],
            req.champion,
            req.opponent,
            role,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return result


@app.get("/tilt/{game_name}/{tag_line}")
def get_tilt(game_name, tag_line):
    if not state["api_key"]:
        raise HTTPException(status_code=503, detail="Riot API key not added")
    try:
        player_riot_id = riot_get(f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"{game_name}#{tag_line} not found")
        raise
    puuid = player_riot_id["puuid"] # lookup account

    # get 10 matches
    match_ids = riot_get(f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&count=10")

    if not match_ids: # accounts w/ 0 games
        raise HTTPException(status_code=404, detail=f"No ranked games found for {game_name}#{tag_line}")

    wins = 0
    for match_id in match_ids: # go through each match and check if player is on the winning team, increment win count
        each_match = riot_get(f"https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}")
        participant = next((player for player in each_match["info"]["participants"] if player["puuid"] == puuid), None)
        if participant and participant["win"]:
            wins += 1

    total = len(match_ids)
    win_rate = wins / total # calculates win percentage, and determines streak
    status = "hot streak" if win_rate >= 0.7 else "cold streak" if win_rate <= 0.3 else "neutral"
    return {"wins": wins, "total": total, "win_rate": win_rate, "status": status}
