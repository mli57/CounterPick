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

- **Frontend:** React & Tailwind
- **Backend:** FastAPI
- **ML:** XGBoost
- **Data:** Riot Games API (match-v5)
- **Database:** SQLite


## Status

| Component | Status |
|---|---|
| Data collection pipeline | Done |
| Role normalization | In progress |
| Feature engineering | Not started |
| Model training | Not started |
| FastAPI backend | Not started |
| React frontend | Not started |

---

## Disclaimer

This project uses the Riot Games API but is not endorsed or certified by Riot Games.