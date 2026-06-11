## Changelog

### v1.0.0 (0.726 AUC): working end to end
- Added gold, XP, CS, and level at 10 and 14 min as features (8 new deltas)
- Fully functional React/TypeScript frontend with shadcn components
- Role fallback logic: off-role picks (e.g. Nasus support) use majority-role stats with a user-facing warning
- Added setup scripts (`setup.bat`, `setup.sh`)
- Committed database for users without a Riot API key

### v0.3.0: First working fullstack
- Connected FastAPI backend (`/champions`, `/predict`) to frontend
- Added laning snapshot stats at 10 and 14 min to `champion_tags`
- Added deadzone filter: drops matchups with gold lead under 500g at 14 min (near-zero leads are not meaningful lane wins)
- React frontend scaffolded and wired to API

### v0.2.0 (0.68 AUC)
- Switched label from game win to lane win (gold lead at 14 min via timeline API), added `lane_outcomes` table
- Added `kills_delta`, `deaths_delta`, `range_delta`, `damage_dealt_delta`, `dmg_mit_delta` features
- Fixed perspective bias towards blue team in `build_features.py` (mirror each row from red's perspective)
- Added stratified k-fold cross-validation (k=5)
- Switched metric from accuracy to AUC-ROC + log loss
- Added `predict.py`

### v0.1.0 (0.635 AUC): First working backend
- Full data pipeline: `pull_matches.py`, `normalize_roles.py`, `derive_tags.py`, `build_features.py`, `train_model.py`
- Even player sampling across divisions I–IV within each bracket
- Initial model: XGBoost on game win label
- Features: `cc_delta`, `dmg_mit_delta`



## Possible Future Additions

- Elo-specific predictions (`elo_bracket` already stored in `matches`, just needs to be added as a feature and retrained)
- Production API key (removes dev key rate limits, enables larger dataset and faster tilt lookups)
- Expanded elo coverage (extend seeding to Iron/Bronze and Master/Grandmaster)
- Automated patch pipeline (scheduled re-run on patch release instead of manual trigger)
- Win rate trend across patches (store historical tags to show whether a champion is rising or falling)
- Contextual notes (map tag combinations to plain English tips for less experienced players)
