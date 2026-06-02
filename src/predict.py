"""
predict.py

How it works:
1. Accepts two champion names & a role
2. looks up each champion's stats from db
3. Computes the delta values between champions
4. Run the model & predict the win probability
5. Warns if either champion's role_share is under FLEX_THRESHOLD

How to run:
    python src/predict.py --db lol_draft.db
"""

import argparse
import sqlite3
import joblib
import logging

# set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

FLEX_THRESHOLD = 0.65
FEATURES = ['cc_delta', 'dmg_mit_delta', 'damage_dealt_delta', 'kills_delta', 'deaths_delta', 'range_delta']

def is_flex(conn, champion_id, role, patch):
    query = """
        SELECT role_share FROM champion_role_majority
        WHERE champion_id = ? AND majority_role = ? AND patch = ?
    """
    result = conn.execute(query, (champion_id, role, patch)).fetchone()
    if result is None:
        return True  # no data, assume flex
    return result[0] < FLEX_THRESHOLD

def get_champion(conn, name, role, patch):
    query = """
        WITH get_champ AS(
            SELECT champion_id, base_range FROM champion_meta
            WHERE champion_name = ?
        ),

        get_stats AS(
            SELECT champion_id, role, patch, 
                avg_cc_time, avg_damage_mitigated, avg_damage_dealt, avg_kills, avg_deaths
            FROM champion_tags
            WHERE role = ? AND patch = ?
        )

        SELECT champion_id, base_range, avg_cc_time, avg_damage_mitigated, avg_damage_dealt, avg_kills, avg_deaths
        FROM get_champ 
        JOIN get_stats USING (champion_id)
    """

    result = conn.execute(query, (name, role, patch)).fetchone()
    if result is None:
        raise ValueError("Champion not found.")
    
    return result

def parse_args():
    # houses the db flags only, so we can point script at different db files.
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="lol_draft.db", help="SQLite database path")
    return parser.parse_args()

def main():
    args = parse_args()
    conn = sqlite3.connect(args.db) # connect to sqlite db
    log.info(f"Connected to {args.db}")

    # Players are always playing on the latest patch
    query = """
    SELECT MAX(patch) FROM champion_tags
    """
    patch = conn.execute(query).fetchone()[0]

    champ1 = input("Enter champion 1: ")#.lower()
    champ2 = input("Enter champion 2: ")#.lower()
    role = input("Enter your role: ").upper()

    champ1_stats = get_champion(conn, champ1, role, patch)
    champ2_stats = get_champion(conn, champ2, role, patch)
    deltas = [champ1_stats[2] - champ2_stats[2], # cc
              champ1_stats[3] - champ2_stats[3], # dmg_mit
              champ1_stats[4] - champ2_stats[4], # dmg_dlt
              champ1_stats[5] - champ2_stats[5], # avg_kill
              champ1_stats[6] - champ2_stats[6], # avg_death
              champ1_stats[1] - champ2_stats[1]  # range
              ]

    if is_flex(conn, champ1_stats[0], role, patch):
        log.warning(f"{champ1} is not commonly played in {role}: prediction may be inaccurate")
    if is_flex(conn, champ2_stats[0], role, patch):
        log.warning(f"{champ2} is not commonly played in {role}: prediction may be inaccurate")

    model = joblib.load("models/model.pkl")
    win_prob = model.predict_proba([deltas])[0][1]
    log.info(f"{champ1} win probability vs {champ2} in {role}: {win_prob:.1%}")


if __name__ == "__main__":
    main()