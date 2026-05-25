"""
pull_matches.py

Collects League ranked match data from Riot's API and stores it in a local SQLite database.

How it works:
0. Pulls static champion data (IDs, names, base range) from Data Dragon -> required before any participant inserts
1. Seeds from ~300 players across four elo brackets (Gold, Platinum, Emerald, Diamond)
2. Fetches each player's PUUID from their summoner profile
3. Pulls the GAMES_PER_PLAYER most recent match IDs per player
4. Downloads full match details (champions, roles, winner, duration, patch) and writes to SQLite

Tables in db:
    matches               (match_id, patch, duration_secs, winning_team, elo_bracket)
    participants          (match_id, team, champion_id, role_raw, role_normalized, win)
    participant_stats     (participant_id, kills, deaths, assists, total_cc_time, damage_taken, damage_mitigated, damage_dealt_to_champions)
    champion_meta         (champion_id, champion_name, base_range)
    champion_role_majority & champion_tags are created here but populated by normalize_roles.py and derive_tags.py

API rate limits:
    Riot's free developer key allows 100 requests every 2 minutes.
    The RateLimiter class handles this automatically by sleeping when approaching the limit.
    Collection of ~18,000 unique matches runs overnight under this constraint.

How to run this file:
  1. Get Riot API key
  2. Set the key as an environment variable:
       $env:RIOT_API_KEY="paste the key here"
  3. Run:
       python pull_matches.py
  4. Additional flags:
       --db      Path to the SQLite database file
       --target  How many unique matches to collect
       --region  Server region: na1, euw1, kr, etc.
"""

import argparse
import logging
import os
import sqlite3
import time
from collections import deque

import requests

# set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


class RateLimiter:
    """
    keeps us under riot's 100 requests/120s limit. Keeps a rolling deque of request timestamps. 
    Before each request, pop expired entries and sleeps if the window is full.
    """
    def __init__(self, max_requests: int = 100, window_secs: float = 120):
        self.max_requests = max_requests
        self.window_secs = window_secs
        self._api_request_times: deque = deque()

    def wait(self):
        time_now = time.time()

        # remove timestamps older than the 120s window, they no longer count against the limit
        while self._api_request_times and self._api_request_times[0] < time_now - self.window_secs:
            self._api_request_times.popleft()

        if len(self._api_request_times) >= self.max_requests:
            sleep_for = self._api_request_times[0] + self.window_secs - time_now + 0.1
            if sleep_for > 0:
                time.sleep(sleep_for)
            time_now = time.time()

        self._api_request_times.append(time_now)


##### parameters
TIERS = ["GOLD", "PLATINUM", "EMERALD", "DIAMOND"]
DIVISIONS = ["I", "II", "III", "IV"]
PLAYERS_PER_BRACKET = 300
GAMES_PER_PLAYER = 20  # keep low!! High games_per_payer may pull in games from multiple balance patches
PLATFORM_REGION_MAP = {
    "na1": "americas",
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",
    "euw1": "europe",
    "eun1": "europe",
    "tr1": "europe",
    "ru": "europe",
    "kr": "asia",
    "jp1": "asia",
}


class RiotAPIClient:
    """
    riot api wrapper. five methods:
        1. get_player_list      fetch one page of players from the ranked ladder
        2. get_puuid            convert a summoner ID to a PUUID (needed for match-v5)
        3. get_match_ids        fetch most recent ranked match IDs for a PUUID
        4. get_match_detail     fetch full match JSON for a match ID
        5. get_champion_meta    champion IDs/names/ranges from Data Dragon (no rate limit needed)
    """
    def __init__(self, api_key: str, platform: str = "na1"):
        self.api_key = api_key
        self.platform = platform.lower()
        self.regional = PLATFORM_REGION_MAP.get(self.platform, "americas")
        self.rl = RateLimiter(max_requests=95,window_secs=120) # conservative limit of 95

        self._session = requests.Session()
        self._session.headers.update({"X-Riot-Token": self.api_key})

    def _get(self, url: str): # use rate limiter
        self.rl.wait()
        response = self._session.get(url)
        response.raise_for_status()
        return response.json()

    def get_player_list(self, tier: str, division: str, page: int = 1):
        url = f"https://{self.platform}.api.riotgames.com/lol/league/v4/entries/RANKED_SOLO_5x5/{tier}/{division}?page={page}"
        return self._get(url)

    def get_puuid(self, summoner_id: str):
        url = f"https://{self.platform}.api.riotgames.com/lol/summoner/v4/summoners/{summoner_id}"
        return self._get(url)["puuid"]

    def get_match_ids(self, puuid: str):
        url = f"https://{self.regional}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&count={GAMES_PER_PLAYER}"  # 420 = ranked solo/duo
        return self._get(url)

    def get_match_detail(self, match_id: str):
        url = f"https://{self.regional}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return self._get(url)

    def get_champion_meta(self):
        # Data Dragon is a static CDN, no auth or rate limiting needed
        version = self._session.get("https://ddragon.leagueoflegends.com/api/versions.json").json()[0]
        data = self._session.get(f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json").json()
        return [
            {
                "champion_id": int(champ["key"]),
                "champion_name": champ["name"],
                "base_range": int(champ["stats"]["attackrange"]),
            }
            for champ in data["data"].values()
        ]


def create_db(conn: sqlite3.Connection):
    """
    sql commands to create database and corresponding tables
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id        TEXT PRIMARY KEY,
            patch           TEXT,
            duration_secs   INTEGER,
            winning_team    INTEGER,    -- 100(blue) or 200(red)
            elo_bracket     TEXT        -- Gold, Platinum, Emerald, Diamond
        );

        CREATE TABLE IF NOT EXISTS participants (
            participant_id  INTEGER PRIMARY KEY,    -- internal autoincrement ID, not Riot's index
            match_id        TEXT REFERENCES matches(match_id),
            champion_id     INTEGER REFERENCES champion_meta(champion_id),
            team            INTEGER,        -- 100(blue) or 200(red)
            win             INTEGER,        -- 1 = win, 0 = loss
            role_raw        TEXT,           -- raw teamPosition from Riot
            role_normalized TEXT            -- filled by normalize_roles.py, NULL until then
        );

        CREATE TABLE IF NOT EXISTS participant_stats (
            participant_id              INTEGER PRIMARY KEY REFERENCES participants(participant_id),
            kills                       INTEGER,
            deaths                      INTEGER,
            assists                     INTEGER,
            total_cc_time               INTEGER,
            damage_taken                INTEGER,
            damage_mitigated            INTEGER,
            damage_dealt_to_champions   INTEGER
        );

        CREATE TABLE IF NOT EXISTS champion_meta (
            champion_id     INTEGER PRIMARY KEY,
            champion_name   TEXT,
            base_range      INTEGER     -- poke proxy in derive_tags.py
        );

        CREATE TABLE IF NOT EXISTS champion_role_majority (
            champion_id     INTEGER REFERENCES champion_meta(champion_id),
            patch           TEXT,
            majority_role   TEXT,
            role_share      REAL,       -- 0.0 to 1.0, threshold for flex warning is 0.65
            PRIMARY KEY (champion_id, patch)
        );

        CREATE TABLE IF NOT EXISTS champion_tags (
            champion_id         INTEGER REFERENCES champion_meta(champion_id),
            role                TEXT,
            patch               TEXT,
            avg_cc_time         REAL,
            avg_damage_mitigated REAL,
            avg_game_duration_wins REAL,
            PRIMARY KEY (champion_id, role, patch)
        );
    """)


def parse_args():
    """
    houses run-specific flags only. structural stuff (tiers, player counts) is in the constants block up top.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--db",     default="lol_draft.db", help="SQLite database path")
    parser.add_argument("--target", type=int, default=25000, help="Target unique match count")
    parser.add_argument("--region", default="na1",           help="Platform region (na1, euw1, kr, …)")
    return parser.parse_args()


def collect_summoner_ids(client: RiotAPIClient):
    """
    grabs up to PLAYERS_PER_BRACKET puuids per tier across all divisions. returns list of (puuid, tier) tuples.
    """
    puuids = set()
    for tier in TIERS:
        players_per_tier = 0 # reset once per tier
        for division in DIVISIONS:
            log.info(f"Collecting summoners from {tier} {division}")
            page = 1
            while players_per_tier < PLAYERS_PER_BRACKET//len(division):  # of games evenly split among divs I, II, III, IV
                if players_per_tier >= PLAYERS_PER_BRACKET//len(division):
                    break
                entries = client.get_player_list(tier, division, page)
                if not entries:
                    break
                for entry in entries:
                    puuids.add((entry["puuid"], tier))
                    players_per_tier += 1
                page += 1
    return list(puuids)


def process_match(client: RiotAPIClient, conn: sqlite3.Connection, match_id: str, elo_bracket: str):
    """
    fetches & inserts one match (matches, participants, participant_stats). skips and returns False if already in db.
    """
    result = conn.execute("SELECT 1 FROM matches WHERE match_id = ?", (match_id,))
    already_exists = result.fetchone()
    if already_exists:
        log.debug(f"Skipping {match_id} — already in db")
        return False

    match_json = client.get_match_detail(match_id)
    info = match_json["info"]

    # 100 = blue side, 200 = red side
    blue_team_won = info["teams"][0]["win"]  # True or False
    if blue_team_won:
        winning_team = 100
    else:
        winning_team = 200

    # insert the match row
    conn.execute(
        "INSERT INTO matches(match_id, patch, duration_secs, winning_team, elo_bracket) VALUES (?, ?, ?, ?, ?)",
        (match_id, info["gameVersion"], info["gameDuration"], winning_team, elo_bracket)
    )

    # insert each of the 10 participants
    for p in info["participants"]:

        # insert basic participant info
        conn.execute(
            "INSERT INTO participants(match_id, champion_id, team, win, role_raw) VALUES (?, ?, ?, ?, ?)",
            (match_id, p["championId"], p["teamId"], int(p["win"]), p["teamPosition"])
        )

        # grab the participant_id sqlite just auto-generated for the row we just inserted
        pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # insert their stats, linked to that participant_id
        # use .get() with a default of 0, some fields don't apply to certain champs or game states(some champs dont have cc)
        conn.execute(
            "INSERT INTO participant_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (pid,
             p.get("kills", 0),
             p.get("deaths", 0),
             p.get("assists", 0),
             p.get("totalTimeCCingOthers", 0),
             p.get("totalDamageTaken", 0),
             p.get("damageSelfMitigated", 0),
             p.get("totalDamageDealtToChampions", 0))
        )

    # save everything
    conn.commit()
    return True


def main():
    """
    sets up db, seeds champion_meta, then collects matches until target is hit.
    """

    args = parse_args()
    log.info(f"Starting collection. target: {args.target} matches, region: {args.region}, db: {args.db}")

    api_key = os.environ.get("RIOT_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("RIOT_API_KEY environment variable not set")

    # opens db file and create it if it doesn't exist
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON")
    create_db(conn)

    # create API client, pull data from DDragon
    client = RiotAPIClient(api_key, args.region)
    champions = client.get_champion_meta()
    conn.executemany(
        "INSERT OR IGNORE INTO champion_meta(champion_id, champion_name, base_range) VALUES (?, ?, ?)",
        [(c["champion_id"], c["champion_name"], c["base_range"]) for c in champions]
    )
    conn.commit()
    log.info(f"Loaded {len(champions)} champions into champion_meta")

    # collect puuids per rank
    puuids = collect_summoner_ids(client)
    log.info(f"Collected {len(puuids)} unique puuids across all brackets")

    # loop over every player, stop once target match count reached
    unique_matches = 0
    for puuid, tier in puuids:
        if unique_matches >= args.target:
            break
        try:
            for match_id in client.get_match_ids(puuid):
                if unique_matches >= args.target:
                    break
                if process_match(client, conn, match_id, tier):
                    unique_matches += 1
                    if unique_matches % 100 == 0:
                        log.info(f"Collected {unique_matches} matches so far")
        except Exception as e:
            log.warning(f"Skipping puuid {puuid}: {e}")

    log.info(f"Done. {unique_matches} unique matches collected into {args.db}")


if __name__ == "__main__":
    main()
