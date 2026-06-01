"""
build_features.py

How it works:
    Gets delta values of average cc time, damage mitigation, and game duration(only for winning teams)
    between two players of the same role, in the same game

How to run this file:
    python src/build_features.py --db test.db 
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
        SELECT 
            a.win,
            ta.avg_cc_time - tb.avg_cc_time AS cc_delta, 
            ta.avg_damage_mitigated - tb.avg_damage_mitigated AS dmg_mit_delta,
            ta.avg_damage_dealt - tb.avg_damage_dealt AS damage_dealt_delta,
            ta.avg_kills - tb.avg_kills AS kills_delta,
            ta.avg_deaths - tb.avg_deaths AS deaths_delta,
            ma.base_range - mb.base_range AS range_delta
        FROM participants a
        JOIN participants b ON b.match_id = a.match_id 
            AND b.role_normalized = a.role_normalized
            AND b.team = 200
        JOIN matches m ON m.match_id = a.match_id
        JOIN champion_tags ta ON ta.champion_id = a.champion_id 
            AND ta.role = a.role_normalized 
            AND ta.patch = m.patch
        JOIN champion_tags tb ON tb.champion_id = b.champion_id 
            AND tb.role = b.role_normalized 
            AND tb.patch = m.patch
        JOIN champion_meta ma ON ma.champion_id = a.champion_id
        JOIN champion_meta mb ON mb.champion_id = b.champion_id
        WHERE a.team = 100
            AND m.duration_secs > 1200
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