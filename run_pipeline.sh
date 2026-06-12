#!/bin/bash
set -e

# echo "Step 1: Pulling data from Riot API: uncomment to pull fresh data from RIOT (requires your own API key)"
# python src/backend/pull_matches.py

echo "Step 2: Normalizing roles"
python src/backend/normalize_roles.py --db test.db

echo "Step 3: Deriving champion tags"
python src/backend/derive_tags.py --db test.db

echo "Step 4: Building features"
python src/backend/build_features.py -db test.db

echo "Step 5: Training Model"
python src/backend/train_model.py

echo "Pipeline complete."
