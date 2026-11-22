"""Trusted mid-task inbox. Explicit add/replace; ordinary busy messages queue.

The database owns admission/order. Only the live coordinator applies additions;
replacement starts after its predecessor has returned and no tool is in flight.
"""
from __future__ import annotations

import json
import re
import uuid

from harness import runtime
from harness.trace import now
from policy import controls, state
from policy.approvals import canonical
from policy.state import db
from sandbox import course

QUEUE_LIMIT = 8
QUESTION_LIMIT = 3
TERMINAL = ("completed", "failed", "cancelled", "replaced", "rolled_back", "rollback_partial")


def _schema(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS message_heads (session_id TEXT PRIMARY KEY, run_id TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS operator_messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, run_id TEXT NOT NULL,
      kind TEXT NOT NULL, text TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL,
      created_at TEXT NOT NULL, answer TEXT);
    """)


def reset():
    with db() as conn:
        _schema(conn)
        conn.execute("DELETE FROM message_heads")
        conn.execute("DELETE FROM operator_messages")


def current_run(session_id):
    with db() as conn:
        _schema(conn)
        row = conn.execute("SELECT run_id FROM message_heads WHERE session_id=?", (session_id,)).fetchone()
    root = runtime.current_run()
    return row[0] if row else (root.run_id if root else session_id)


def set_head(session_id, run_id):
    with db() as conn:
        _schema(conn)
        conn.execute("INSERT OR REPLACE INTO message_heads VALUES (?,?)", (session_id, run_id))


def records(session_id=None):
    with db() as conn:
        _schema(conn)
        rows = conn.execute("SELECT * FROM operator_messages ORDER BY id").fetchall()
    return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows
            if session_id is None or r["session_id"] == session_id]


def _questions(text):
    text = re.sub(r"^process\s+", "", text.strip(), flags=re.I)
    if not re.fullmatch(r"SYN-Q-[A-Za-z0-9_-]+(?:[ ,]+SYN-Q-[A-Za-z0-9_-]+)*", text):
        raise ValueError("Specify question IDs, for example /add SYN-Q-deadline.")
    ids = list(dict.fromkeys(re.findall(r"SYN-Q-[A-Za-z0-9_-]+", text)))
    if len(ids) > QUESTION_LIMIT or any(q not in {r["id"] for r in course.records("question")} for q in ids):
        raise ValueError("Select at most three existing inbox question IDs.")
    return ids


def owned_effects(run_id):
    keys = list(dict.fromkeys(c["action_key"] for c in controls.calls(run_id) if c["action_key"]))
    effects = {e["action_key"]: e for e in course.effects()}
    for call in controls.calls(run_id):
        if call["tool"] == "course_send_reply":
            effects[call["action_key"]] = course.effect(call["arguments"]["effect_id"])
    return list({effects[k]["id"]: effects[k] for k in keys if k in effects}.values())


def _enqueue(session_id, run_id, kind, text, payload):
    with db() as conn:
        _schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        if kind != "replace":
            count = conn.execute("SELECT COUNT(*) FROM operator_messages WHERE session_id=? AND kind!='replace' AND status IN ('pending','observed','executing','held')",
                                 (session_id,)).fetchone()[0]
            if count >= QUEUE_LIMIT:
                raise ValueError("Message queue is full (8). Stop commands remain available.")
        if kind == "add":
            row = conn.execute("SELECT status,snapshot FROM control_runs WHERE run_id=? AND session_id=?", (run_id, session_id)).fetchone()
            if row is None or row[0] not in ("active", "waiting_approval", "waiting_outside"):
                raise ValueError("There is no active task accepting additions.")
            task = json.loads(row[1] or "{}").get("task", {})
            selected = set(task.get("question_ids", []))
            for r in conn.execute("SELECT payload FROM operator_messages WHERE run_id=? AND kind='add' AND status!='cancelled'", (run_id,)):
                selected.update(json.loads(r[0])["question_ids"])
            if not task or len(selected | set(payload["question_ids"])) > QUESTION_LIMIT:
                raise ValueError("The combined task can contain at most three question IDs.")
        if kind == "replace":
            prior = conn.execute("SELECT 1 FROM operator_messages WHERE session_id=? AND kind='replace' AND status IN ('pending','executing')", (session_id,)).fetchone()
            if prior:
                raise ValueError("A replacement is already waiting; inspect /messages.")
            # Same database as dispatch: a later old-run call cannot slip through.
            conn.execute("INSERT OR REPLACE INTO stops VALUES (?,1,?)", (run_id, now()))
            conn.execute("UPDATE control_runs SET status='replaced',updated_at=? WHERE run_id=?", (now(), run_id))
            conn.execute("UPDATE operator_messages SET status='cancelled' WHERE run_id=? AND kind='add' AND status IN ('pending','observed','executing')", (run_id,))
        identifier = conn.execute("INSERT INTO operator_messages(session_id,run_id,kind,text,payload,status,created_at) VALUES (?,?,?,?,?,'pending',?)",
                                  (session_id, run_id, kind, text, canonical(payload), now())).lastrowid
    return identifier


def route(session_id, text, trace, *, busy):
    stripped = text.strip()
    verb, _, remainder = stripped.partition(" ")
    run_id = current_run(session_id)
    if verb == "/messages":
        return "\n".join(f"Message {r['id']} [{r['kind']}/{r['status']}]: {r['answer'] or r['text']}" for r in records(session_id)) or "No operator messages are queued."
    if verb not in ("/add", "/replace", "/queue", "/reject"):
        if not busy or stripped.startswith("/"):
            return None
        verb, remainder = "/queue", stripped
    try:
        if verb == "/reject":
            trace.event("operator_message", disposition="rejected", source="trusted_operator", text=remainder)
            return "Message rejected immediately; it was not queued or executed."
        if not remainder.strip():
            raise ValueError(f"{verb} needs question IDs or message text.")
        if verb == "/queue" and remainder.strip().startswith("/"):
            raise ValueError("Queue ordinary task/status text; send control commands directly, never through the queue.")
        payload = {}
        if verb == "/add":
            payload["question_ids"] = _questions(remainder)
        if verb == "/replace":
            rows = [r for r in controls.runs(session_id) if r["run_id"] == run_id]
            if not rows or rows[0]["status"] in TERMINAL:
                raise ValueError("No live or held task is available to replace.")
            undo = []
            rollback_all = False
            if remainder.startswith("--rollback "):
                rollback_all, remainder = True, remainder[len("--rollback "):]
            elif remainder.startswith("--undo "):
                selection, sep, remainder = remainder[len("--undo "):].partition(" ")
                if not sep:
                    raise ValueError("Use /replace --undo EFFECT_ID[,EFFECT_ID] QUESTION_ID.")
                undo = selection.split(",")
                if any(i not in {e["id"] for e in owned_effects(run_id)} for i in undo):
                    raise ValueError("Undo selections must belong to the task being replaced.")
            ids = _questions(remainder)
            payload = {"question_ids": ids, "new_run_id": f"{session_id}:replacement:{uuid.uuid4().hex[:12]}",
                       "undo_ids": undo, "rollback_all": rollback_all}
        identifier = _enqueue(session_id, run_id, verb[1:], remainder, payload)
        trace.event("operator_message", message_id=identifier, control_run_id=run_id,
                    disposition=verb[1:], source="trusted_operator")
        if verb == "/replace":
            controls._withdraw(run_id)
            controls.snapshot(run_id, trace)
            effects = owned_effects(run_id)
            listing = ", ".join(f"{e['id']} ({e['status']})" for e in effects) or "none recorded yet"
            return f"Replacement {identifier} saved; old task stopped. Existing effects: {listing}. " + (
                "Selected compensation runs after any in-flight call finishes." if undo or rollback_all else
                f"Effects are retained; use /rollback {run_id} to request their compensation.")
        return f"Message {identifier} saved as {verb[1:]}; the current task is preserved."
    except ValueError as exc:
        trace.event("operator_message", disposition="rejected", source="trusted_operator", reason=str(exc))
        return str(exc)


def observe(run_id, trace, messages=None):
    with db() as conn:
        _schema(conn)
        rows = conn.execute("SELECT * FROM operator_messages WHERE run_id=? AND kind='add' AND status='pending' ORDER BY id", (run_id,)).fetchall()
        for row in rows:
            conn.execute("UPDATE operator_messages SET status='observed' WHERE id=? AND status='pending'", (row["id"],))
    for row in rows:
        ids = json.loads(row["payload"])["question_ids"]
        trace.event("operator_message_observed", message_id=row["id"], control_run_id=run_id,
                    source="trusted_operator", question_ids=ids)
        if messages is not None:
            messages.append({"role": "user", "content": canonical({"trusted_operator_addition": ids,
                "handling": "Coordinator will process these selected questions after the current segment; finish this segment normally."})})


def additions_or_finish(run_id):
    """Atomic end barrier: no accepted addition can fall behind completion."""
    with db() as conn:
        _schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        stopped = conn.execute("SELECT stopped FROM stops WHERE run_id=?", (run_id,)).fetchone()
        if stopped and stopped[0]:
            from agent.bounds import Halt
            raise Halt("run_stopped", "Task was interrupted before completing additions.")
        rows = conn.execute("SELECT * FROM operator_messages WHERE run_id=? AND kind='add' AND status IN ('pending','observed') ORDER BY id", (run_id,)).fetchall()
        if not rows:
            conn.execute("UPDATE control_runs SET status='completed',updated_at=? WHERE run_id=?", (now(), run_id))
            return []
        for row in rows:
            conn.execute("UPDATE operator_messages SET status='executing' WHERE id=?", (row["id"],))
    return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]


def finish(identifier, answer):
    with db() as conn:
        _schema(conn)
        conn.execute("UPDATE operator_messages SET status='done',answer=? WHERE id=? AND status='executing'", (answer, identifier))


def hold_message(identifier, answer):
    with db() as conn:
        _schema(conn)
        conn.execute("UPDATE operator_messages SET status='held',answer=? WHERE id=? AND status='executing'", (answer, identifier))


def set_execution(identifier, run_id):
    with db() as conn:
        _schema(conn)
        row = conn.execute("SELECT payload FROM operator_messages WHERE id=?", (identifier,)).fetchone()
        payload = json.loads(row[0])
        payload["execution_run_id"] = run_id
        conn.execute("UPDATE operator_messages SET payload=? WHERE id=?", (canonical(payload), identifier))


def next_deferred(session_id):
    run_id = current_run(session_id)
    row = next((r for r in controls.runs(session_id) if r["run_id"] == run_id), None)
    if row and row["status"] not in TERMINAL:
        return None
    if any(c["status"] == "inflight" for c in controls.calls(run_id)):
        return None
    with db() as conn:
        _schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        item = conn.execute("SELECT * FROM operator_messages WHERE session_id=? AND kind IN ('replace','queue') AND status='pending' ORDER BY CASE kind WHEN 'replace' THEN 0 ELSE 1 END,id LIMIT 1", (session_id,)).fetchone()
        if item:
            conn.execute("UPDATE operator_messages SET status='executing' WHERE id=?", (item["id"],))
    return {**dict(item), "payload": json.loads(item["payload"])} if item else None
