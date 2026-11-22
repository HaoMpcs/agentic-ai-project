"""Small provenance memory for confirmed operator facts across sessions."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from harness.paths import state_dir


def db():
    connection = sqlite3.connect(state_dir() / "memory.sqlite3", timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE IF NOT EXISTS memories (
        kind TEXT NOT NULL, name TEXT NOT NULL, value TEXT NOT NULL,
        source_type TEXT NOT NULL, source_id TEXT NOT NULL,
        created_at TEXT NOT NULL, superseded_at TEXT,
        PRIMARY KEY(kind,name,created_at))""")
    return connection


def put(kind: str, name: str, value: str, *, source_type: str, source_id: str):
    if kind != "operator_preference" or not value.strip():
        raise ValueError("Only an explicit non-empty operator preference may be remembered.")
    now = datetime.now(timezone.utc).isoformat()
    with db() as connection:
        connection.execute("UPDATE memories SET superseded_at=? WHERE kind=? AND name=? AND superseded_at IS NULL",
                           (now, kind, name))
        connection.execute("INSERT INTO memories VALUES (?,?,?,?,?,?,NULL)",
                           (kind, name, value.strip()[:500], source_type, source_id, now))
    return get(kind, name)


def get(kind: str, name: str):
    with db() as connection:
        row = connection.execute("SELECT * FROM memories WHERE kind=? AND name=? AND superseded_at IS NULL ORDER BY created_at DESC LIMIT 1",
                                 (kind, name)).fetchone()
    return dict(row) if row else None


def active(kind: str | None = None):
    with db() as connection:
        rows = connection.execute("SELECT * FROM memories WHERE superseded_at IS NULL ORDER BY kind,name").fetchall()
    return [dict(row) for row in rows if kind is None or row["kind"] == kind]


def reset():
    with db() as connection:
        connection.execute("DELETE FROM memories")


def prompt_records():
    return [{"kind": row["kind"], "name": row["name"], "value": row["value"],
             "provenance": {"source_type": row["source_type"], "source_id": row["source_id"],
                            "created_at": row["created_at"]}}
            for row in active("operator_preference")]
