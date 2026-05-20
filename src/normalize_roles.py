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


def calculate_role_majority(conn):
    """
    use sql queries to calculate the majority role of each champion
    """

    query = """

    WITH role_counts AS(
        SELECT champion_id, role_raw, COUNT(*) AS games_per_role, patch 
        FROM participants
        JOIN matches USING (match_id)
        GROUP BY champion_id, role_raw, patch
    ),

    totals AS(
        SELECT champion_id, COUNT(*) AS games_total, patch
        FROM participants
        JOIN matches USING (match_id)
        GROUP BY champion_id, patch
    )
    SELECT champion_id, role_raw, games_per_role, games_per_role * 1.0 / games_total AS role_percentage, patch
    FROM role_counts
    JOIN totals USING (champion_id, patch)
    """

    rows = conn.execute(query).fetchall()
    best = {}
    for row in rows:
        champion_id, role_raw, games_per_role, role_percentage, patch = row
        key = (champion_id, patch)

        if(key not in best) or (best[key][3] < row[3]):
            best[key] = row

    return best


def save_role_majority(conn, best):
    """
    Save the calculated champion role majority to db
    """

    for key, value in best.items():
        query = """
        INSERT OR REPLACE INTO champion_role_majority (champion_id, patch, majority_role, role_share) VALUES (?, ?, ?, ?)
    """
        conn.execute(query,(best[key][0], best[key][4], best[key][1], best[key][3]))
    conn.commit()


def update_role_normalized(conn):
    """
    add the correct normalized champion role into the participants table
    """

    query = """
    UPDATE participants SET role_normalized = role_raw WHERE role_raw != ''
    """
    conn.execute(query)
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

    # store result from calculating role majority in table
    normalized_table = calculate_role_majority(conn)
    log.info(f"Found majority roles for {len(normalized_table)} (champion, patch) pairs")
    for key, row in list(normalized_table.items())[:5]: # paste first entries into chat
        log.info(f"{key}: {row}")

    # save table to db
    save_role_majority(conn, normalized_table)

    # save role data from raw to normalized
    update_role_normalized(conn)
    log.info("role_normalized updated in participants")



if __name__ == "__main__":
    main()