# LoL Matchup Analyzer

Work in progress, core pipeline under active development.

A web app that tells you how your champion matchup plays out and when you are strongest, built for use during champ select. Made for a personal project.

---

## Features

**Matchup Lookup**
Input your champion, your opponent's, and your role. Get back a predicted win rate, an early/mid/late power breakdown, and a summary of how the matchup plays out.

**Tilt Indicator**
Look up any summoner to see their win rate over their last 20 games. Quick way to gauge a teammate or opponent during champ select.


## How It Works

Pulls ranked match data from the Riot API across Gold, Platinum, Emerald, and Diamond. Processes raw in-game stats like CC time, damage output, and game duration into per-champion behavioral profiles, then trains an XGBoost model to predict matchup win rates and power spikes by game phase. Rather than looking up specific champion pairings, the model learns each champion's properties independently, so uncommon matchups still get a reasonable prediction.

For a full breakdown of the technical decisions and architecture, see [DESIGN.md](docs/DESIGN.md).


## Stack

- **Frontend:** React + TypeScript, Vite, Tailwind CSS, shadcn
- **Backend:** FastAPI
- **ML:** XGBoost
- **Data:** Riot Games API (match-v5)
- **Database:** SQLite


## Setup

Clone the repo, then run the setup script specific for your device. It installs Python dependencies and frontend Node modules in one step.

**Windows:**
```bat
setup.bat
```

**Mac/Linux:**
```bash
chmod +x setup.sh && ./setup.sh
```

To start the app after setup:
```bash
# Backend (from project root)
uvicorn src.api.main:app --reload

# Frontend (in a separate terminal)
cd frontend
npm run dev
```

---

## Status

| Component | Status |
|---|---|
| Data collection pipeline | Done |
| Role normalization | Done |
| Feature engineering | Done |
| Model training | Done |
| FastAPI backend | Done |
| React/TypeScript frontend | Done |

Currently working on adding the power spike breakdown, tilt indicator, and a better model(w/ features for abilities)

---

## Disclaimer

This project uses the Riot Games API but is not endorsed or certified by Riot Games.
