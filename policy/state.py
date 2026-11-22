"""Part 2 control records, separate from Part 1's execution checkpoints.

All storage resolves under state_dir at call time. The service is the trusted
writer; neither student messages nor tool arguments can change these rules.
"""
from __future__ import annotations

import contextlib
import sqlite3

from harness.paths import state_dir
from harness.trace import now


@contextlib.contextmanager
def db():
    conn = sqlite3.connect(state_dir() / "autonomy.sqlite3", timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS limits (
          session_id TEXT NOT NULL, target TEXT NOT NULL, mode TEXT NOT NULL,
          source TEXT NOT NULL, updated_at TEXT NOT NULL,
          PRIMARY KEY(session_id,target));
        CREATE TABLE IF NOT EXISTS stops (
          run_id TEXT PRIMARY KEY, stopped INTEGER NOT NULL, updated_at TEXT NOT NULL);
        """)
        with conn:
            yield conn
    finally:
        conn.close()


def reset():
    with db() as conn:
        conn.execute("DELETE FROM limits")
        conn.execute("DELETE FROM stops")


def set_limit(session_id: str, target: str, mode: str, source: str):
    if not session_id or target not in ("drafts", "writes", "sends") or mode not in ("approval", "deny"):
        raise ValueError("Use a session, target drafts/writes/sends, and mode approval/deny.")
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO limits VALUES (?,?,?,?,?)",
                     (session_id, target, mode, source, now()))


def limits(session_id: str) -> list[dict]:
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM limits WHERE session_id=? ORDER BY target", (session_id,))]


def set_stopped(run_id: str, stopped: bool):
    """Integration point for the forthcoming Part 2 stop/resume controller."""
    if not run_id or not isinstance(stopped, bool):
        raise ValueError("A run ID and boolean stop state are required.")
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO stops VALUES (?,?,?)", (run_id, int(stopped), now()))


def is_stopped(run_id: str) -> bool:
    with db() as conn:
        row = conn.execute("SELECT stopped FROM stops WHERE run_id=?", (run_id,)).fetchone()
    return bool(row and row[0])
