"""Immediate operator interrupts and action snapshots; not a task replay engine."""
from __future__ import annotations

import json
from datetime import datetime

from harness.trace import now
from policy import state
from policy.approvals import canonical
from policy.state import db


def _schema(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS control_runs (
      run_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, status TEXT NOT NULL,
      updated_at TEXT NOT NULL, observed_at TEXT, snapshot TEXT);
    CREATE TABLE IF NOT EXISTS control_calls (
      id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, tool TEXT NOT NULL,
      arguments TEXT NOT NULL, action_key TEXT, status TEXT NOT NULL,
      result TEXT, started_at TEXT NOT NULL, finished_at TEXT);
    """)


def reset():
    with db() as conn:
        _schema(conn)
        conn.execute("DELETE FROM control_runs")
        conn.execute("DELETE FROM control_calls")


def ensure(session_id, run_id, trace):
    with db() as conn:
        _schema(conn)
        inserted = conn.execute("INSERT OR IGNORE INTO control_runs VALUES (?,?,'active',?,NULL,NULL)",
                                (run_id, session_id, now())).rowcount
    if inserted:
        trace.event("run_live", control_run_id=run_id, notice="Operator: this run is live; /stop interrupts later calls.")
        trace.progress(f"Run {run_id} is live. Use /stop to interrupt it.")


def runs(session_id=None):
    with db() as conn:
        _schema(conn)
        rows = conn.execute("SELECT * FROM control_runs ORDER BY updated_at,run_id").fetchall()
    return [dict(r) for r in rows if session_id is None or r["session_id"] == session_id]


def set_status(run_id, status):
    with db() as conn:
        _schema(conn)
        conn.execute("UPDATE control_runs SET status=?,updated_at=? WHERE run_id=?", (status, now(), run_id))


def calls(run_id):
    with db() as conn:
        _schema(conn)
        rows = conn.execute("SELECT * FROM control_calls WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
    return [{**dict(r), "arguments": json.loads(r["arguments"]),
             "result": json.loads(r["result"]) if r["result"] else None} for r in rows]


def dispatch(run_id, name, args, key):
    with db() as conn:
        _schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        stopped = conn.execute("SELECT stopped FROM stops WHERE run_id=?", (run_id,)).fetchone()
        if stopped and stopped[0]:
            from policy.hook import PolicyBlocked
            raise PolicyBlocked("run/stopped", "prohibited", "stopped")
        return conn.execute("INSERT INTO control_calls(run_id,tool,arguments,action_key,status,started_at) VALUES (?,?,?,?,'inflight',?)",
                            (run_id, name, canonical(args), key, now())).lastrowid


def complete(identifier, result):
    with db() as conn:
        _schema(conn)
        conn.execute("UPDATE control_calls SET status=?,result=?,finished_at=? WHERE id=?",
                     ("error" if result.is_error else "completed", canonical(result.data), now(), identifier))


def snapshot(run_id, trace):
    previous = next((r for r in runs() if r["run_id"] == run_id), {})
    prior = json.loads(previous["snapshot"]) if previous.get("snapshot") else {}
    saved = {"control_run_id": run_id, "calls": calls(run_id), "saved_at": now(),
             "task": prior.get("task"),
             "scope": "Part 2 action snapshot; full model/plan continuation belongs to Part 1"}
    with db() as conn:
        _schema(conn)
        conn.execute("UPDATE control_runs SET snapshot=? WHERE run_id=?", (canonical(saved), run_id))
    trace.event("control_snapshot", **saved)
    return saved


def remember_task(run_id, request, question_ids, route):
    saved = {"task": {"operator_request": request, "question_ids": question_ids, "route": route}}
    with db() as conn:
        _schema(conn)
        conn.execute("UPDATE control_runs SET snapshot=? WHERE run_id=?", (canonical(saved), run_id))


def observe(run_id, trace):
    if not state.is_stopped(run_id):
        return
    at = now()
    with db() as conn:
        _schema(conn)
        stop = conn.execute("SELECT updated_at FROM stops WHERE run_id=?", (run_id,)).fetchone()
        changed = conn.execute("UPDATE control_runs SET observed_at=? WHERE run_id=? AND observed_at IS NULL", (at, run_id)).rowcount
    if changed and stop:
        seconds = max(0.0, (datetime.fromisoformat(at) - datetime.fromisoformat(stop[0])).total_seconds())
        trace.event("stop_observed", control_run_id=run_id, latency_s=seconds)


def _withdraw(run_id):
    from policy import approvals
    for row in approvals.records():
        if row["run_id"] == run_id:
            with db() as conn:
                conn.execute("UPDATE approvals SET status='withdrawn' WHERE id=? AND status='pending'", (row["id"],))


def _reask(run_id, trace):
    from policy import approvals
    import uuid
    result = []
    for row in approvals.records(("withdrawn",)):
        if row["run_id"] != run_id:
            continue
        identifier = "approval-" + uuid.uuid4().hex[:24]
        with db() as conn:
            changed = conn.execute("UPDATE approvals SET status='superseded' WHERE id=? AND status='withdrawn'", (row["id"],)).rowcount
            if changed:
                conn.execute("INSERT INTO approvals(id,session_id,run_id,status,created_at,payload) VALUES (?,?,?,'pending',?,?)",
                             (identifier, row["session_id"], run_id, now(), canonical(row["payload"])))
        if changed:
            result.append(identifier)
            trace.event("approval_reasked", approval_id=identifier, previous_id=row["id"], control_run_id=run_id)
    return result


def _end_holds(run_id):
    from policy import escalations
    escalations.records()  # Ensure the domain tables exist before the updates.
    with db() as conn:
        conn.execute("UPDATE escalations SET status='cancelled' WHERE run_id=? AND status IN ('held','awaiting_recovery')", (run_id,))
        conn.execute("UPDATE approvals SET status='cancelled' WHERE run_id=? AND status='withdrawn'", (run_id,))
    from policy import messages
    for message in messages.records():
        if message["run_id"] == run_id or message["payload"].get("execution_run_id") == run_id:
            with db() as conn:
                conn.execute("UPDATE operator_messages SET status='cancelled' WHERE id=? AND status IN ('pending','observed','executing','held')", (message["id"],))


def command(session_id, text, trace):
    words = text.strip().split()
    if not words or words[0] not in ("/stop", "/cancel", "/resume", "/rollback"):
        return None
    if len(words) > 2:
        return "Use /stop, /cancel, /resume or /rollback, optionally followed by this session's run ID."
    candidates = runs(session_id)
    if len(words) == 2:
        candidates = [r for r in candidates if r["run_id"] == words[1]]
    else:
        candidates = [r for r in candidates if r["status"] not in ("completed", "failed", "cancelled", "replaced", "rolled_back", "rollback_partial")]
    if not candidates:
        return "No live or held run matches this session; nothing was changed."
    messages = []
    for row in candidates:
        run_id = row["run_id"]
        verb = words[0]
        if row["status"] in ("completed", "failed", "cancelled", "replaced", "rolled_back", "rollback_partial") and verb != "/rollback":
            messages.append(f"{run_id} is {row['status']}; no run was restarted.")
            continue
        if verb == "/resume":
            if row["status"] != "stopped":
                messages.append(f"{run_id} is not stopped; no flag was lifted.")
                continue
            from agent import service
            from harness.paths import state_dir
            turn_lock = service._locks[(str(state_dir().resolve()), session_id)]
            if turn_lock.locked():
                messages.append(f"{run_id}: the interrupted turn is still finishing; it remains stopped.")
                continue
            if any(c["status"] == "inflight" for c in calls(run_id)):
                messages.append(f"{run_id} still has an in-flight call; it remains stopped.")
                continue
            state.set_stopped(run_id, False)
            reasked = _reask(run_id, trace)
            set_status(run_id, "waiting_approval" if reasked else "awaiting_continuation")
            trace.event("run_resumed", control_run_id=run_id, notice="Operator: held run resumed; execution remains bounded by policy.")
            trace.progress(f"Run {run_id} resumed; its saved state is available.")
            messages.append(f"{run_id}: stop lifted. " + ("Review the newly issued approval." if reasked else "Saved actions retained; Part 1 must continue the remaining task."))
            continue
        # Commands never wait on the service turn lock or the active model call.
        state.set_stopped(run_id, True)
        with db() as conn:
            _schema(conn)
            conn.execute("UPDATE control_runs SET status=?,updated_at=?,observed_at=NULL WHERE run_id=?",
                         ("cancelled" if verb == "/cancel" else "stopped", now(), run_id))
        _withdraw(run_id)
        trace.event("run_stop", control_run_id=run_id, command=verb)
        saved = snapshot(run_id, trace)
        if verb == "/rollback":
            if any(c["status"] == "inflight" for c in saved["calls"]):
                messages.append(f"{run_id}: stopped; let the in-flight call finish, then repeat /rollback.")
                continue
            from agent.tools import Registry
            registry = Registry(session_id, [], run_id=run_id)
            keys = list(dict.fromkeys(c["action_key"] for c in reversed(saved["calls"]) if c["action_key"]))
            from sandbox import course
            effects = {e["action_key"]: e for e in course.effects()}
            for call in saved["calls"]:
                if call["tool"] == "course_send_reply":
                    effects[call["action_key"]] = course.effect(call["arguments"]["effect_id"])
            outcomes = []
            for key in keys:
                effect = effects.get(key)
                if effect:
                    outcomes.append(registry.compensate(effect["id"]))
            set_status(run_id, "rollback_partial" if any(x.endswith(": none") for x in outcomes) else "rolled_back")
            _end_holds(run_id)
            snapshot(run_id, trace)
            messages.append(f"{run_id}: " + ("; ".join(outcomes) or "none: no compensatable effect"))
        elif verb == "/cancel":
            _end_holds(run_id)
            messages.append(f"{run_id}: cancelled permanently; existing effects remain.")
        else:
            messages.append(f"{run_id}: stopped. In-flight calls may finish; later calls are refused.")
    return "\n".join(messages)
