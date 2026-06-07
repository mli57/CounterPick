"""
derive_tags.py

How it works: 
    joins participants, participant_stats, and matches to compute
    per-champion per-role per-patch averages, then writes them to champion_tags.

How to run this file: 
    python src/backend/derive_tags.py --db lol_draft.db
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

def add_lane_stat_columns(conn):
    for col in ["avg_gold_10", "avg_gold_14", "avg_xp_10", "avg_xp_14",
                  "avg_cs_lane_10", "avg_cs_lane_14", "avg_level_10", "avg_level_14"]:  
        try:
            conn.execute(f"ALTER TABLE champion_tags ADD COLUMN {col} REAL")
        except sqlite3.OperationalError: pass
    conn.commit()

def derive_tags(conn):
    # aggregate avg cc time, damage mitigated, and win-only game duration per (champion, role, patch). 
    # CASE WHEN filters duration to wins only;
    # AVG ignores NULLs so losers don't drag the average down.
    query = """
    SELECT 
          participants.champion_id, 
          participants.role_normalized, 
          matches.patch, 
          AVG(total_cc_time),
          AVG(damage_mitigated),
          AVG(CASE WHEN participants.win = 1 THEN duration_secs ELSE NULL END),
          AVG(CASE WHEN participants.win = 0 THEN duration_secs ELSE NULL END),
          AVG(damage_dealt_to_champions),
          AVG(kills),
          AVG(deaths),
          AVG(CASE WHEN pls.frame = 10 THEN pls.gold     END),
          AVG(CASE WHEN pls.frame = 14 THEN pls.gold     END),
          AVG(CASE WHEN pls.frame = 10 THEN pls.xp       END),
          AVG(CASE WHEN pls.frame = 14 THEN pls.xp       END),
          AVG(CASE WHEN pls.frame = 10 THEN pls.cs_lane  END),
          AVG(CASE WHEN pls.frame = 14 THEN pls.cs_lane  END),
          AVG(CASE WHEN pls.frame = 10 THEN pls.level    END),
          AVG(CASE WHEN pls.frame = 14 THEN pls.level    END)
      FROM participants
      JOIN participant_stats USING (participant_id)
      JOIN matches USING (match_id)
      LEFT JOIN participant_lane_stats pls
          ON  pls.match_id = participants.match_id
          AND pls.team     = participants.team
          AND pls.role     = participants.role_raw
      WHERE participants.role_normalized IS NOT NULL
      GROUP BY participants.champion_id, participants.role_normalized, matches.patch
    """

    return conn.execute(query).fetchall()

def save_derived_tags(conn, rows):
    query = """
    INSERT OR REPLACE INTO champion_tags (
        champion_id, role, patch, avg_cc_time, avg_damage_mitigated, avg_game_duration_wins, 
        avg_game_duration_losses, avg_damage_dealt, avg_kills, avg_deaths,

        avg_gold_10, avg_gold_14, avg_xp_10, avg_xp_14, 
        avg_cs_lane_10, avg_cs_lane_14, avg_level_10, avg_level_14
    ) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,   ?, ?, ?, ?, ?, ?, ?, ?)
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

    add_lane_stat_columns(conn)

    derived_tag = derive_tags(conn)
    save_derived_tags(conn, derived_tag)

if __name__ == "__main__":
    main()