import sqlite3
from typing import Optional


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _create_schema(conn)
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS persons (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT NOT NULL,
            title               TEXT,
            company             TEXT,
            domain              TEXT,
            linkedin_url        TEXT,
            apollo_id           TEXT UNIQUE,
            exposure_score      INTEGER DEFAULT 0,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS baseline_videos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id       INTEGER REFERENCES persons(id),
            video_id        TEXT UNIQUE,
            title           TEXT,
            channel_id      TEXT,
            channel_name    TEXT,
            published_at    TEXT,
            audio_path      TEXT,
            embedding_path  TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS candidate_videos (
            id                          INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id                   INTEGER REFERENCES persons(id),
            video_id                    TEXT UNIQUE,
            title                       TEXT,
            channel_id                  TEXT,
            channel_name                TEXT,
            channel_created_at          TEXT,
            channel_subscriber_count    INTEGER,
            channel_verified            INTEGER DEFAULT 0,
            published_at                TEXT,
            view_count                  INTEGER,
            like_count                  INTEGER,
            description                 TEXT,
            tags                        TEXT,
            duration                    TEXT,
            audio_path                  TEXT,
            created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scores (
            id                          INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_video_id          INTEGER REFERENCES candidate_videos(id),
            person_id                   INTEGER REFERENCES persons(id),
            source_credibility_score    INTEGER DEFAULT 0,
            account_age_score           INTEGER DEFAULT 0,
            metadata_score              INTEGER DEFAULT 0,
            voice_match_score           INTEGER DEFAULT 0,
            total_score                 INTEGER DEFAULT 0,
            risk_level                  TEXT,
            voice_similarity            REAL,
            score_notes                 TEXT,
            created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()


def upsert_person(
    conn: sqlite3.Connection,
    name: str,
    title: Optional[str],
    company: str,
    domain: str,
    linkedin_url: Optional[str] = None,
    apollo_id: Optional[str] = None,
) -> int:
    cur = conn.cursor()
    if apollo_id:
        cur.execute("SELECT id FROM persons WHERE apollo_id = ?", (apollo_id,))
        row = cur.fetchone()
        if row:
            return row["id"]
    cur.execute(
        "SELECT id FROM persons WHERE name = ? AND company = ?",
        (name, company),
    )
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute(
        "INSERT INTO persons (name, title, company, domain, linkedin_url, apollo_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, title, company, domain, linkedin_url, apollo_id),
    )
    conn.commit()
    return cur.lastrowid


def set_exposure_score(conn: sqlite3.Connection, person_id: int, score: int) -> None:
    conn.execute(
        "UPDATE persons SET exposure_score = ? WHERE id = ?",
        (score, person_id),
    )
    conn.commit()


def upsert_baseline_video(
    conn: sqlite3.Connection,
    person_id: int,
    video_id: str,
    title: str,
    channel_id: str,
    channel_name: str,
    published_at: str,
) -> int:
    cur = conn.cursor()
    cur.execute("SELECT id FROM baseline_videos WHERE video_id = ?", (video_id,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute(
        "INSERT INTO baseline_videos "
        "(person_id, video_id, title, channel_id, channel_name, published_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (person_id, video_id, title, channel_id, channel_name, published_at),
    )
    conn.commit()
    return cur.lastrowid


def set_baseline_audio(
    conn: sqlite3.Connection,
    video_id: str,
    audio_path: Optional[str],
    embedding_path: Optional[str],
) -> None:
    conn.execute(
        "UPDATE baseline_videos SET audio_path = ?, embedding_path = ? WHERE video_id = ?",
        (audio_path, embedding_path, video_id),
    )
    conn.commit()


def upsert_candidate_video(
    conn: sqlite3.Connection,
    person_id: int,
    video_id: str,
    title: str,
    channel_id: str,
    channel_name: str,
    channel_created_at: Optional[str],
    channel_subscriber_count: Optional[int],
    channel_verified: bool,
    published_at: str,
    view_count: Optional[int],
    like_count: Optional[int],
    description: Optional[str],
    tags: Optional[str],
    duration: Optional[str],
) -> int:
    cur = conn.cursor()
    cur.execute("SELECT id FROM candidate_videos WHERE video_id = ?", (video_id,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute(
        """INSERT INTO candidate_videos
           (person_id, video_id, title, channel_id, channel_name, channel_created_at,
            channel_subscriber_count, channel_verified, published_at, view_count,
            like_count, description, tags, duration)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            person_id, video_id, title, channel_id, channel_name, channel_created_at,
            channel_subscriber_count, int(channel_verified), published_at, view_count,
            like_count, description, tags, duration,
        ),
    )
    conn.commit()
    return cur.lastrowid


def set_candidate_audio(
    conn: sqlite3.Connection, video_id: str, audio_path: Optional[str]
) -> None:
    conn.execute(
        "UPDATE candidate_videos SET audio_path = ? WHERE video_id = ?",
        (audio_path, video_id),
    )
    conn.commit()


def insert_score(
    conn: sqlite3.Connection,
    candidate_video_id: int,
    person_id: int,
    source_credibility: int,
    account_age: int,
    metadata: int,
    voice_match: int,
    total: int,
    risk_level: str,
    voice_similarity: Optional[float],
    notes: str,
) -> int:
    conn.execute(
        "DELETE FROM scores WHERE candidate_video_id = ?",
        (candidate_video_id,),
    )
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO scores
           (candidate_video_id, person_id, source_credibility_score, account_age_score,
            metadata_score, voice_match_score, total_score, risk_level,
            voice_similarity, score_notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            candidate_video_id, person_id, source_credibility, account_age,
            metadata, voice_match, total, risk_level, voice_similarity, notes,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_persons(conn: sqlite3.Connection) -> list:
    return conn.execute(
        "SELECT * FROM persons ORDER BY exposure_score DESC"
    ).fetchall()


def get_baseline_videos(conn: sqlite3.Connection, person_id: int) -> list:
    return conn.execute(
        "SELECT * FROM baseline_videos WHERE person_id = ?",
        (person_id,),
    ).fetchall()


def get_candidate_videos(conn: sqlite3.Connection, person_id: int) -> list:
    return conn.execute(
        "SELECT * FROM candidate_videos WHERE person_id = ?",
        (person_id,),
    ).fetchall()


def get_score_for_candidate(conn: sqlite3.Connection, candidate_video_id: int):
    return conn.execute(
        "SELECT * FROM scores WHERE candidate_video_id = ?",
        (candidate_video_id,),
    ).fetchone()
