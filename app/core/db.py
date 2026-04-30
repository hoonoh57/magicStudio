from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    genre TEXT NOT NULL,
    target_format TEXT NOT NULL,
    root_path TEXT NOT NULL,
    market_score REAL DEFAULT 0,
    production_score REAL DEFAULT 0,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ideas (
    idea_id TEXT PRIMARY KEY,
    project_id TEXT,
    raw_text TEXT NOT NULL,
    detected_genre TEXT,
    core_hook TEXT,
    target_audience TEXT,
    format_candidates TEXT,
    risk_flags TEXT,
    market_score REAL DEFAULT 0,
    production_score REAL DEFAULT 0,
    decision TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS episodes (
    episode_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    episode_no INTEGER NOT NULL,
    title TEXT NOT NULL,
    scenario_text TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenes (
    scene_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    scene_no INTEGER NOT NULL,
    title TEXT NOT NULL,
    dramatic_function TEXT,
    duration_sec REAL DEFAULT 0,
    vml_json TEXT DEFAULT '{}',
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    episode_id TEXT,
    scene_id TEXT,
    asset_type TEXT NOT NULL,
    path TEXT NOT NULL,
    description TEXT,
    quality_score REAL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    episode_id TEXT,
    scene_id TEXT,
    review_type TEXT NOT NULL,
    score REAL NOT NULL,
    decision TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def execute(self, sql: str, params: Iterable[object] = ()) -> None:
        with self.connect() as conn:
            conn.execute(sql, tuple(params))
            conn.commit()

    def fetch_one(self, sql: str, params: Iterable[object] = ()) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(sql, tuple(params)).fetchone()

    def fetch_all(self, sql: str, params: Iterable[object] = ()) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute(sql, tuple(params)).fetchall())
