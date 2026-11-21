# Author: Jingyu Huang (CNetID: jyhuang28).
"""Durable run state and a call journal; separate from B's cross-session memory."""
from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta

from harness import runtime
from harness.paths import state_dir

TERMINAL = {"completed", "failed", "cancelled"}


@contextlib.contextmanager
def db():
    connection = sqlite3.connect(state_dir() / "execution.sqlite3", timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript("""
        PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS runs (
          run_key TEXT PRIMARY KEY, session_id TEXT NOT NULL, number INTEGER NOT NULL,
          status TEXT NOT NULL, owner INTEGER, data TEXT NOT NULL,
          UNIQUE(session_id, number));
        CREATE TABLE IF NOT EXISTS calls (
          run_key TEXT NOT NULL, position INTEGER NOT NULL, status TEXT NOT NULL,
          name TEXT NOT NULL, arguments TEXT NOT NULL, action_key TEXT, result TEXT,
          PRIMARY KEY(run_key, position));
        CREATE TABLE IF NOT EXISTS outbox (
          action_key TEXT PRIMARY KEY, run_key TEXT NOT NULL, thread_id TEXT NOT NULL,
          body TEXT NOT NULL, since_id INTEGER NOT NULL, message_id INTEGER);
        CREATE UNIQUE INDEX IF NOT EXISTS one_wait_per_thread
          ON runs(json_extract(data, '$.wait.thread_id')) WHERE status='waiting_external';
        """)
        with connection:
            yield connection
    finally:
        connection.close()


def reset():
    with db() as connection:
        for table in ("calls", "outbox", "runs"):
            connection.execute(f"DELETE FROM {table}")


def _decode(row):
    if row is None:
        return None
    return {**json.loads(row["data"]), "status": row["status"]}


def load(run_key):
    with db() as connection:
        return _decode(connection.execute("SELECT * FROM runs WHERE run_key=?", (run_key,)).fetchone())


def latest(session_id, *, live=False):
    with db() as connection:
        query = "SELECT * FROM runs WHERE session_id=?"
        if live:
            query += " AND status NOT IN ('completed','failed','cancelled')"
        return _decode(connection.execute(query + " ORDER BY number DESC LIMIT 1", (session_id,)).fetchone())


def live_runs():
    """Read adapter for C's queue and B's later-session startup inventory."""
    with db() as connection:
        rows = connection.execute("SELECT * FROM runs WHERE status NOT IN ('completed','failed','cancelled') ORDER BY session_id,number").fetchall()
    return [_decode(row) for row in rows]


def create(session_id, request, question_ids, route):
    with db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        number = connection.execute("SELECT COALESCE(MAX(number),0)+1 FROM runs WHERE session_id=?", (session_id,)).fetchone()[0]
        run = runtime.current_run()
        key = f"{run.run_id}:{number}" if run else f"{session_id}:{number}"
        data = {"run_key": key, "session_id": session_id, "number": number,
                "request": request, "question_ids": question_ids, "route": route,
                "mode": "sync", "snapshot": {}, "status": "running", "stop": False}
        data["plan_enabled"] = runtime.switch("plan.batch", "off") == "on"
        data["code_enabled"] = runtime.switch("code_calls.batch", "off") == "on"
        connection.execute("INSERT INTO runs VALUES (?,?,?,?,NULL,?)",
                           (key, session_id, number, "running", json.dumps(data)))
    return data


def save(data, *, preserve_control=False):
    # A JSON round trip rejects connections, open files and accidental live objects.
    with db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        previous = _decode(connection.execute("SELECT * FROM runs WHERE run_key=?", (data["run_key"],)).fetchone())
        if preserve_control and previous and (previous["stop"] or previous["status"] in ("held", "stopped", "cancelled")):
            data.update(status=previous["status"], stop=previous["stop"], hold_reason=previous.get("hold_reason", ""))
        encoded = json.dumps(data, allow_nan=False)
        connection.execute("UPDATE runs SET status=?,data=? WHERE run_key=?",
                           (data["status"], encoded, data["run_key"]))


def claim(run_key):
    with db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT owner FROM runs WHERE run_key=?", (run_key,)).fetchone()
        if row is None:
            raise ValueError("Unknown run key.")
        owner = row[0]
        identity = f"{os.getpid()}:{threading.get_ident()}"
        if owner and str(owner) != identity:
            try:
                os.kill(int(str(owner).split(":")[0]), 0)
            except ProcessLookupError:
                pass
            else:
                raise RuntimeError("Run is active in another process; no concurrent replay allowed.")
        connection.execute("UPDATE runs SET owner=? WHERE run_key=?", (identity, run_key))


def release(run_key):
    with db() as connection:
        connection.execute("UPDATE runs SET owner=NULL WHERE run_key=? AND owner=?",
                           (run_key, f"{os.getpid()}:{threading.get_ident()}"))


def control(run_key, *, status, stop, reason="", releasing=False):
    """Change only control fields atomically, preserving concurrent progress."""
    with db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        data = _decode(connection.execute("SELECT * FROM runs WHERE run_key=?", (run_key,)).fetchone())
        if data is None or data["status"] in TERMINAL:
            raise ValueError("No live run has that key.")
        if releasing and data["status"] not in ("held", "stopped"):
            raise ValueError("Only a held run can be released.")
        data.update(status=status, stop=stop, hold_reason=reason)
        connection.execute("UPDATE runs SET status=?,data=? WHERE run_key=?", (status, json.dumps(data), run_key))
    return data


def call(run_key, position):
    with db() as connection:
        row = connection.execute("SELECT * FROM calls WHERE run_key=? AND position=?", (run_key, position)).fetchone()
    if row is None:
        return None
    return {**dict(row), "arguments": json.loads(row["arguments"]),
            "result": json.loads(row["result"]) if row["result"] else None}


def prepare(run_key, position, name, arguments, key):
    with db() as connection:
        connection.execute("INSERT OR IGNORE INTO calls VALUES (?,?,?,?,?,?,NULL)",
                           (run_key, position, "prepared", name, json.dumps(arguments), key))
    return call(run_key, position)


def complete(run_key, position, result):
    with db() as connection:
        connection.execute("UPDATE calls SET status='completed',result=? WHERE run_key=? AND position=?",
                           (json.dumps(result), run_key, position))


def calls(run_key):
    with db() as connection:
        positions = [row[0] for row in connection.execute("SELECT position FROM calls WHERE run_key=? ORDER BY position", (run_key,))]
    return [call(run_key, position) for position in positions]


def waiting(thread_id):
    with db() as connection:
        rows = connection.execute("SELECT * FROM runs WHERE status='waiting_external' ORDER BY number").fetchall()
    return next((data for row in rows if (data := _decode(row)).get("wait", {}).get("thread_id") == thread_id), None)


def now():
    from sandbox import course
    return datetime.fromisoformat(course.record("clock", "SYN-CLOCK")["now"])


def deadline(hours=48):
    return (now() + timedelta(hours=hours)).isoformat()


def outbox(key):
    with db() as connection:
        row = connection.execute("SELECT * FROM outbox WHERE action_key=?", (key,)).fetchone()
    return dict(row) if row else None


def prepare_send(key, run_key, thread_id, body, since_id):
    with db() as connection:
        connection.execute("INSERT OR IGNORE INTO outbox VALUES (?,?,?,?,?,NULL)",
                           (key, run_key, thread_id, body, since_id))
    return outbox(key)


def confirm_send(key, message_id):
    with db() as connection:
        connection.execute("UPDATE outbox SET message_id=? WHERE action_key=?", (message_id, key))


def history(session_id):
    """B's adapter can read operational history without importing agent code."""
    with db() as connection:
        return [_decode(row) for row in connection.execute("SELECT * FROM runs WHERE session_id=? ORDER BY number", (session_id,))]
