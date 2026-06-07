"""
build_features.py

How it works:
1. For each game, participants from both sides in the same role are paired. 
2. Their stat deltas (blue minus red) are calculated using aggregated champion averages from champion_tags.
3. Label is lane_winner from lane_outcomes (1 = blue laner was ahead in gold at 14 min).
    ***Games inside the dead zone (|gold lead| =< dead-zone) are dropped because a near-zero lead is not a lane win***
4. Each row is mirrored from red's perspective to fix perspective bias and also doubles the training data.
5. Outputs data/output.csv.

Features: cc_delta, dmg_mit_delta, damage_dealt_delta, kills_delta, deaths_delta, range_delta,
          gold_14_delta, xp_14_delta, cs_lane_14_delta, level_14_delta,
          gold_10_delta, xp_10_delta, cs_lane_10_delta, level_10_delta

How to run:
    python src/backend/build_features.py --db lol_draft.db --deadzone 500
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

def get_matchups(conn, deadzone):
    query = """
        -- label: was the blue laner ahead in gold at 14 min?
        SELECT
            CASE WHEN outcome.blue_gold_lead_14 > 0 THEN 1 ELSE 0 END AS win,

            blue_tags.avg_cc_time - red_tags.avg_cc_time,
            blue_tags.avg_damage_mitigated - red_tags.avg_damage_mitigated,
            blue_tags.avg_damage_dealt - red_tags.avg_damage_dealt,
            blue_tags.avg_kills - red_tags.avg_kills,
            blue_tags.avg_deaths - red_tags.avg_deaths,
            blue_meta.base_range - red_meta.base_range,

            blue_tags.avg_gold_14 - red_tags.avg_gold_14,
            blue_tags.avg_xp_14 - red_tags.avg_xp_14,
            blue_tags.avg_cs_lane_14 - red_tags.avg_cs_lane_14,
            blue_tags.avg_level_14 - red_tags.avg_level_14,

            blue_tags.avg_gold_10 - red_tags.avg_gold_10,
            blue_tags.avg_xp_10 - red_tags.avg_xp_10,
            blue_tags.avg_cs_lane_10 - red_tags.avg_cs_lane_10,
            blue_tags.avg_level_10 - red_tags.avg_level_10

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
            AND ABS(outcome.blue_gold_lead_14) > ? -- drop deadzone
    """
    rows = conn.execute(query, (deadzone,)).fetchall()

    mirrored = [(1 - win, -cc, -dmg_mit, -dmg_dealt, -kills, -deaths, -range_d,
                 -g14, -xp14, -cs14, -lvl14, -g10, -xp10, -cs10, -lvl10)
                for win, cc, dmg_mit, dmg_dealt, kills, deaths, range_d,
                    g14, xp14, cs14, lvl14, g10, xp10, cs10, lvl10 in rows]

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
    parser.add_argument("--deadzone", type=int, default=500, help="Drop games where gold lead at 14 =< this many gold")
    return parser.parse_args()

def main():
    #declare parse_args to get --db from command line
    args = parse_args()
    conn = sqlite3.connect(args.db) # connect to sqlite db
    log.info(f"Connected to {args.db}")

    rows = get_matchups(conn, args.deadzone)
    log.info(f"{len(rows)} rows after deadzone={args.deadzone}g and mirroring")

    header = ['win', 'cc_delta', 'dmg_mit_delta', 'damage_dealt_delta', 'kills_delta', 'deaths_delta', 'range_delta',
              'gold_14_delta', 'xp_14_delta', 'cs_lane_14_delta', 'level_14_delta',
              'gold_10_delta', 'xp_10_delta', 'cs_lane_10_delta', 'level_10_delta']
    write_to_csv(rows, "data/output.csv", header)
    log.info("Wrote data/output.csv")

if __name__ == "__main__":
    main()