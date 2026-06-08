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
                avg_cc_time, avg_damage_mitigated, avg_damage_dealt, avg_kills, avg_deaths,
                avg_gold_14, avg_xp_14, avg_cs_lane_14, avg_level_14,
                avg_gold_10, avg_xp_10, avg_cs_lane_10, avg_level_10,
                avg_game_duration_wins, avg_game_duration_losses
            FROM champion_tags
            WHERE role = ? AND patch = ?
        )

        SELECT champion_id, base_range,
               avg_cc_time, avg_damage_mitigated, avg_damage_dealt, avg_kills, avg_deaths,
               avg_gold_14, avg_xp_14, avg_cs_lane_14, avg_level_14,
               avg_gold_10, avg_xp_10, avg_cs_lane_10, avg_level_10,
               avg_game_duration_wins, avg_game_duration_losses
        FROM get_champ 
        JOIN get_stats USING (champion_id)
    """

    result = conn.execute(query, (name, role, patch)).fetchone()
    if result is not None:
        return result, None  # (stats, fallback_role)

    # fall back to majority role if no stats found for the chosen role(E.g Fiora support)
    fallback_query = """
        SELECT majority_role FROM champion_role_majority
        JOIN champion_meta USING (champion_id)
        WHERE champion_name = ? AND patch = ?
    """
    row = conn.execute(fallback_query, (name, patch)).fetchone()
    if row is None:
        raise ValueError(f"{name} not found in database.")

    fallback_role = row[0]
    result = conn.execute(query, (name, fallback_role, patch)).fetchone()
    if result is None:
        raise ValueError(f"No stats found for {name}.")

    return result, fallback_role

def phase_label(win_dur, loss_dur):
    if win_dur is None or loss_dur is None:
        return "even scaling"
    diff = win_dur - loss_dur  # negative = wins faster = early, positive = wins slower = late
    if diff < -120:
        return "strong early"
    if diff > 120:
        return "strong late"
    return "even scaling"

def load_model(path="models/model.pkl"):
    return joblib.load(path)

def predict_matchup(conn, model, champ1, champ2, role):
    patch = conn.execute("SELECT MAX(patch) FROM champion_tags").fetchone()[0]

    champ1_stats, champ1_fallback = get_champion(conn, champ1, role, patch)
    champ2_stats, champ2_fallback = get_champion(conn, champ2, role, patch)

    # stat delta: champ minus opponent, treating NULL as 0
    def d(a, b):
        return (a or 0) - (b or 0)

    deltas = [
        d(champ1_stats[2],  champ2_stats[2]),   # cc
        d(champ1_stats[3],  champ2_stats[3]),   # dmg_mit
        d(champ1_stats[4],  champ2_stats[4]),   # dmg_dealt
        d(champ1_stats[5],  champ2_stats[5]),   # kills
        d(champ1_stats[6],  champ2_stats[6]),   # deaths
        d(champ1_stats[1],  champ2_stats[1]),   # range
        d(champ1_stats[7],  champ2_stats[7]),   # gold_14
        d(champ1_stats[8],  champ2_stats[8]),   # xp_14
        d(champ1_stats[9],  champ2_stats[9]),   # cs_lane_14
        d(champ1_stats[10], champ2_stats[10]),  # level_14
        d(champ1_stats[11], champ2_stats[11]),  # gold_10
        d(champ1_stats[12], champ2_stats[12]),  # xp_10
        d(champ1_stats[13], champ2_stats[13]),  # cs_lane_10
        d(champ1_stats[14], champ2_stats[14]),  # level_10
    ]

    warnings = []
    if champ1_fallback:
        warnings.append(f"No {role} data for {champ1}: using stats for {champ1_fallback} instead, predictions may be inaccurate")
    elif is_flex(conn, champ1_stats[0], role, patch):
        warnings.append(f"{champ1} is not commonly played in {role}: prediction may be inaccurate")

    if champ2_fallback:
        warnings.append(f"No {role} data for {champ2}: using stats for {champ2_fallback} instead, predictions may be inaccurate")
    elif is_flex(conn, champ2_stats[0], role, patch):
        warnings.append(f"{champ2} is not commonly played in {role}: prediction may be inaccurate")

    win_prob = float(model.predict_proba([deltas])[0][1])
    return {
        "win_probability": win_prob,
        "warnings": warnings,
        "champion_phase": phase_label(champ1_stats[15], champ1_stats[16]),
        "opponent_phase": phase_label(champ2_stats[15], champ2_stats[16]),
    }


def parse_args():
    # houses the db flags only, so we can point script at different db files.
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="lol_draft.db", help="SQLite database path")
    return parser.parse_args()

def main():
    args = parse_args()
    conn = sqlite3.connect(args.db)
    log.info(f"Connected to {args.db}")

    champ1 = input("Enter champion 1: ")
    champ2 = input("Enter champion 2: ")
    role = input("Enter your role: ").upper()

    model = load_model()
    result = predict_matchup(conn, model, champ1, champ2, role)

    for w in result["warnings"]:
        log.warning(w)
    log.info(f"{champ1} win probability vs {champ2} in {role}: {result['win_probability']:.1%}")


if __name__ == "__main__":
    main()