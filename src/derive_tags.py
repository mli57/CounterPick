"""
derive_tags.py

How it works: 
    joins participants, participant_stats, and matches to compute
    per-champion per-role per-patch averages, then writes them to champion_tags.

How to run this file: 
    python src/derive_tags.py --db lol_draft.db
"""

import argparse
import sqlite3
import logging

# set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

def derive_tags(conn):
    # aggregate avg cc time, damage mitigated, and win-only game duration per (champion, role, patch). 
    # CASE WHEN filters duration to wins only;
    # AVG ignores NULLs so losers don't drag the average down.
    query = """
    SELECT 
        champion_id, 
        role_normalized, 
        patch, 
        AVG(total_cc_time) AS avg_cc_time, 
        AVG(damage_mitigated) AS avg_dmg_mitigated, 
        AVG(CASE WHEN win = 1 THEN duration_secs ELSE NULL END) AS avg_game_duration_wins,
        AVG(CASE WHEN win = 0 THEN duration_secs ELSE NULL END) AS avg_game_duration_losses
    FROM participants
    JOIN participant_stats USING (participant_id)
    JOIN matches USING (match_id)
    WHERE role_normalized IS NOT NULL
    GROUP BY champion_id, role_normalized, patch
    """

    return conn.execute(query).fetchall()

def save_derived_tags(conn, rows):
    query = """
    INSERT OR REPLACE INTO champion_tags (champion_id, role, patch, avg_cc_time, avg_damage_mitigated, avg_game_duration_wins, avg_game_duration_losses) VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    for row in rows:
        conn.execute(query, row)
    conn.commit()

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

    derived_tag = derive_tags(conn)
    save_derived_tags(conn, derived_tag)

if __name__ == "__main__":
    main()