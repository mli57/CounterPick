# Design Doc

## What Is It

A web app for champ select. You put in your champion, your opponent, and your role. It tells you:

1. How favored you are to win the lane (as a win probability)
2. Which stage of the game each champion is strongest

Secondary feature: summoner lookup to check recent win rate (tilt check).

## Software Structure

| Layer | File | Does |
|---|---|---|
| Pipeline | `pull_matches.py` | Riot API -> SQLite |
| | `normalize_roles.py` | role cleaning -> champion_role_majority |
| | `derive_tags.py` | aggregate stats -> champion_tags |
| | `build_features.py` | SQLite -> feature vectors |
| | `train_model.py` | features -> model.pkl |
| Inference | `predict.py` | user input + model.pkl -> result |
| Backend | FastAPI server | serves predict.py, handles tilt API calls |
| Frontend | React + TypeScript + Tailwind + shadcn | matchup input, results display, tilt lookup |

## Data Flow

```
COLLECTION
Data Dragon -> pull_matches.py -> SQLite (champion_meta)   <- must run before participant inserts
Riot API    -> pull_matches.py -> SQLite (matches, participants, participant_stats)
            -> normalize_roles.py -> SQLite (champion_role_majority)
            -> derive_tags.py -> [validate] -> SQLite (champion_tags)

TRAINING
SQLite -> build_features.py -> data/output.csv -> train_model.py -> model.pkl

INFERENCE (per query)
User input -> predict.py -> matchup WR + phase breakdown + warnings

TILT (per query, no ML)
Summoner name -> live Riot API -> last 20 games -> win rate + flag
```

## Data Collection

Games are taken from multiple brackets instead of Challenger-only. Challenger reflects a meta irrelevant to most users.

| Bracket | Seed players | Games/user | Raw pulls |
|---|---|---|---|
| Gold | 300 | 20 | 6,000 |
| Platinum | 300 | 20 | 6,000 |
| Diamond | 300 | 20 | 6,000 |
| Emerald | 300 | 20 | 6,000 |
| Total | 1,200 | | ~24,000 raw / ~18,000 unique |

**Why 20 Most Recent Games**

Balance patches drop very often. Pulling more games per player drags in data from patches where champion strengths were different, so 20 games keeps the dataset anchored to the current meta. Riot's ladder endpoints also only surface active players, so the seed is naturally filtered.

**Patch Transitions**

Accuracy dips right after a major patch and recovers as new games accumulate. The pipeline is designed to be re-run per patch rather than maintaining one growing dataset.

## Database Breakdown

| Table | Stores |
|---|---|
| `matches` | one row per game: patch, duration, winning team, bracket |
| `participants` | one row per player per game: champion, team, role |
| `participant_stats` | CC time, damage, kills/deaths per participant |
| `champion_meta` | static champion data from Data Dragon (name, base range) |
| `champion_role_majority` | majority role per (champion, patch), populated by `normalize_roles.py` |
| `champion_tags` | aggregated stat profile per (champion, role, patch), populated by `derive_tags.py` |
| `lane_outcomes` | gold lead at 14 min per role per match, used as the lane win label |

## Role Normalization

Riot's raw `lane` and `role` fields are unreliable. `teamPosition` from match-v5 is used as the primary role label throughout.

`normalize_roles.py` runs after collection:
1. For each `(champion_id, patch)`, counts games per `teamPosition` bucket
2. Records the majority role and share (e.g. Pantheon is chosen as support 60% of the time)
3. Populates `role_normalized` in `participants` from `role_raw`
4. Populates `champion_role_majority`

`build_features.py` only uses majority-role games for per-role baselines. `predict.py` prints warning for off-role queries rather than a hard block:

> "Pantheon is primarily a support pick (60% of games). Predictions for mid may be less reliable."

## Tag Derivation

Before anything gets wired into `build_features.py`, `derive_tags.py` outputs a ranked champion list per tag to eyeball against what it should be.

Example: `engage = avg_cc_time >= X` should surface Malphite, Leona, Nautilus at the top. If Lux appears (has a root but isn't an engage champion), the threshold gets adjusted. Tags only get committed once the list looks right.

Because `champion_tags` is keyed per role, validation runs per role too. Gragas-top should look like a tank; Gragas-jungle should look like engage.

## How the Model Works

I did not use the simple approach (filter to games where Champion A faced Champion B, compute win rate) because it is just a lookup table. This breaks on sparse matchups, which occurs frequently.

Instead, the model trains on all games and learns each champion as a set of properties: CC output, damage profile, durability, phase power. When asked "Zed vs Orianna mid," for example, it combines what it knows about each champion independently. 

By building a reliable profile on each champ, the model can make accurate predictions even if it's only faced a specific opponent 30 times. This allows sparse matchups to still get reasonable predictions, and meta shifts flow through naturally on each patch re-run.

**Feature Vector**

Built by `build_features.py`, used identically at training and inference:

- `cc_delta` (avg CC time, blue minus red)
- `dmg_mit_delta` (avg damage mitigated)
- `damage_dealt_delta` (avg damage dealt to champions)
- `kills_delta` (avg kills)
- `deaths_delta` (avg deaths)
- `range_delta` (base attack range, from `champion_meta`)
- `gold_14_delta`, `xp_14_delta`, `cs_lane_14_delta`, `level_14_delta` (early laning stats at 14 min)
- `gold_10_delta`, `xp_10_delta`, `cs_lane_10_delta`, `level_10_delta` (early laning stats at 10 min)

**Lane Win Label**

The model predicts lane win, not game win. Label is derived from the match timeline: gold differential at 14 minutes per role(crucial, it represents all other statistics in game). If the blue-side laner is ahead in gold at 14 by a nontrivial margin(at least 500g), label = 1.

**Phase Breakdown**

Win rate is separated by game duration per champion:
- Wins clustering under 25 min: early dominant
- Wins clustering over 35 min: late dominant
- Balanced: even scaling

Output is plain English ("strong early, strong late, etc."), not raw numbers.

**Model**

XGBoost classifier. XGBoost builds an bunch of decision trees where each tree corrects the errors of the previous one, making it well suited for tabular data with mixed feature types.

Target is lane win (1/0). The model is trained offline and saved to `model.pkl`, then loaded by `predict.py` at query time so there is no training cost per request.

Two metrics are tracked:
- **AUC-ROC**: measures how well the model ranks wins above losses. 0.5 is random, 1.0 is perfect. This is the primary signal for whether the model is learning anything useful.
- **Log loss**: checks whether the predicted probabilities are well calibrated, not just whether the ranking is correct. A model can have good AUC but still output overconfident or underconfident probabilities.

## Known Limitations

- Accuracy dips at patch start, intentional not a bug
- Dev key rate limits dataset ceiling, pulling data is slow
- Phase inference attributes team outcomes to individual champions, some noise unavoidable
- Poke inferred from base range, approximation not a perfect signal
- Flex picks below 0.65 role share get soft predictions with a user-facing warning
- Jungle influence on lane gold lead is not controlled for, noted as a disclaimer in the UI