"""
build_features.py

How it works:
1. For each game, participants from both sides in the same role are paired. 
2. Their stat deltas (blue minus red) are calculated using aggregated champion averages from champion_tags.
3. Label is lane_winner from lane_outcomes (1 = blue laner was ahead in gold at 14 min).
4. Each row is mirrored from red's perspective to fix perspective bias and also doubles the training data.
5. Outputs data/output.csv.

Features: cc_delta, dmg_mit_delta, damage_dealt_delta, kills_delta, deaths_delta, range_delta

How to run:
    python src/backend/build_features.py --db lol_draft.db
"""
import argparse
import sqlite3
import logging
import csv

# set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

def get_matchups(conn):
    query = """
        -- label: was the blue laner ahead in gold at 14 min?
        SELECT
            outcome.lane_winner AS win,

            -- feature deltas: blue minus red for each stat
            blue_tags.avg_cc_time - red_tags.avg_cc_time AS cc_delta,
            blue_tags.avg_damage_mitigated - red_tags.avg_damage_mitigated AS dmg_mit_delta,
            blue_tags.avg_damage_dealt - red_tags.avg_damage_dealt AS damage_dealt_delta,
            blue_tags.avg_kills - red_tags.avg_kills AS kills_delta,
            blue_tags.avg_deaths - red_tags.avg_deaths AS deaths_delta,
            blue_meta.base_range - red_meta.base_range AS range_delta

        -- one row per role per game: blue side participant vs red side participant
        FROM participants blue
        JOIN participants red ON red.match_id = blue.match_id
            AND red.role_normalized = blue.role_normalized
            AND red.team = 200

        -- match metadata (patch, duration)
        JOIN matches match ON match.match_id = blue.match_id

        -- lane outcome label (gold diff at 14 min)
        JOIN lane_outcomes outcome ON outcome.match_id = blue.match_id
            AND outcome.role = blue.role_normalized

        -- aggregated champion stats per role per patch
        JOIN champion_tags blue_tags ON blue_tags.champion_id = blue.champion_id
            AND blue_tags.role = blue.role_normalized
            AND blue_tags.patch = match.patch
        JOIN champion_tags red_tags ON red_tags.champion_id = red.champion_id
            AND red_tags.role = red.role_normalized
            AND red_tags.patch = match.patch

        -- static champion range (melee vs ranged proxy)
        JOIN champion_meta blue_meta ON blue_meta.champion_id = blue.champion_id
        JOIN champion_meta red_meta ON red_meta.champion_id = red.champion_id

        WHERE blue.team = 100
            AND match.duration_secs > 1200  -- exclude remakes and very short games
    """
    rows = conn.execute(query).fetchall()

    # mirror each row from red's perspective: flip the sign of every delta and invert the win label.
    # this fixes the perspective bias (model was only ever seeing blue - red) and this doubles training data for free.
    mirrored = [(1 - win, -cc, -dmg_mit, -dmg_dealt, -kills, -deaths, -range_d)
                for win, cc, dmg_mit, dmg_dealt, kills, deaths, range_d in rows]

    return rows + mirrored

def write_to_csv(data, output_path, header):
    with open(output_path, 'w', newline='') as file:
        writer = csv.writer(file) # makes csv file, write header and all rows
        writer.writerow(header)
        writer.writerows(data)

def parse_args():
    """
    houses the db flags only, so we can point script at different db files.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="lol_draft.db", help="SQLite database path")
    return parser.parse_args()

def main():
    #declare parse_args to get --db from command line
    args = parse_args()
    conn = sqlite3.connect(args.db) # connect to sqlite db
    log.info(f"Connected to {args.db}")

    header = ['win', 'cc_delta', 'dmg_mit_delta', 'damage_dealt_delta', 'kills_delta', 'deaths_delta', 'range_delta']
    write_to_csv(get_matchups(conn), "data/output.csv", header)

if __name__ == "__main__":
    main()