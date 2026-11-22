"""Named unresolved-write signal and durable operator hold; no guessed replay.

Part 2 owns the hold and human packet. Part 1 owns the full run checkpoint and
same-key retry/continuation when inspection proves that no effect exists.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from harness import runtime
from harness.trace import now
from policy import state
from policy.approvals import canonical, digest
from policy.state import db
from sandbox import course

ACTIVE = ("held", "awaiting_recovery")


def config():
    import yaml
    from policy.hook import POLICY_PATH
    value = yaml.safe_load(POLICY_PATH.read_text())["review"]
    if (type(value.get("daily_cap")) is not int or value["daily_cap"] < 0
            or type(value.get("hold_timeout_seconds")) is not int or value["hold_timeout_seconds"] <= 0):
        raise ValueError("Invalid reviewer budget or hold timeout.")
    ZoneInfo(value["timezone"])
    return value


def _schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS escalations (
      id TEXT PRIMARY KEY, session_id TEXT NOT NULL, run_id TEXT NOT NULL,
      status TEXT NOT NULL, created_at TEXT NOT NULL, deadline TEXT NOT NULL,
      notified INTEGER NOT NULL, payload TEXT NOT NULL, resolved_at TEXT,
      resolved_by TEXT, resolution TEXT)""")


def _row(row):
    if row is None:
        raise ValueError("No such escalation.")
    result = dict(row)
    result["payload"] = json.loads(result["payload"])
    result["timed_out"] = datetime.fromisoformat(now()) >= datetime.fromisoformat(result["deadline"])
    result["over_cap"] = not bool(result["notified"])
    return result


def get(identifier):
    with db() as conn:
        _schema(conn)
        return _row(conn.execute("SELECT * FROM escalations WHERE id=?", (identifier,)).fetchone())


def records(statuses=ACTIVE):
    with db() as conn:
        _schema(conn)
        rows = conn.execute("SELECT * FROM escalations ORDER BY created_at,id").fetchall()
    return [_row(r) for r in rows if r["status"] in statuses]


def reset():
    with db() as conn:
        _schema(conn)
        conn.execute("DELETE FROM escalations")


def _review_count(conn, at, settings):
    zone = ZoneInfo(settings["timezone"])
    day = datetime.fromisoformat(at).astimezone(zone).date()
    times = [r[0] for r in conn.execute("SELECT created_at FROM escalations WHERE notified=1")]
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='approvals'").fetchone():
        times += [r[0] for r in conn.execute("SELECT created_at FROM approvals")]
    return sum(datetime.fromisoformat(t).astimezone(zone).date() == day for t in times)


def hold(registry, name, args, key, *, caller, step=0, plan_step=None, call_id=None):
    settings = config()
    at = now()
    packet = {"attempted": f"{name} on {args['question_id']} under its saved action key",
              "reason": "The write returned an ambiguous outcome; it may already have committed.",
              "needed": "TA: inspect the saved action and confirm an identical existing effect; absent effects require Part 1 recovery."}
    payload = {"signal": "write_outcome_unknown", "tool": name, "arguments": args,
               "action_key": key, "caller": caller, "step": step, "plan_step": plan_step, "call_id": call_id,
               "allowed_questions": sorted(registry.allowed), "read_questions": sorted(registry.read_questions),
               "read_documents": sorted(registry.read_docs), "approval_id": registry.approval_id,
               "switches": runtime.switches(), "packet": packet}
    identifier = "escalation-" + digest([registry.session_id, registry.control_run_id, name, key, args])[:24]
    deadline = (datetime.fromisoformat(at) + timedelta(seconds=settings["hold_timeout_seconds"])).isoformat()
    with db() as conn:
        _schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT id FROM escalations WHERE id=?", (identifier,)).fetchone()
        if existing is None:
            notified = _review_count(conn, at, settings) < settings["daily_cap"]
            conn.execute("INSERT INTO escalations VALUES (?,?,?,'held',?,?,?,?,NULL,NULL,NULL)",
                         (identifier, registry.session_id, registry.control_run_id, at, deadline, int(notified), canonical(payload)))
    row = get(identifier)
    registry.trace.event("escalation_held", escalation_id=identifier, signal="write_outcome_unknown",
                         control_run_id=registry.control_run_id, over_cap=row["over_cap"], deadline=row["deadline"])
    if existing is None and row["notified"]:
        registry.trace.event("escalation_packet", escalation_id=identifier, **packet)
    return row


def inspect(identifier):
    row = get(identifier)
    p = row["payload"]
    if p["tool"] == "course_send_reply":
        import channel
        message = channel.sent_for_key(p["action_key"])
        if message is None:
            return "absent", None
        same = message.thread_id == p["arguments"]["question_id"] and message.sender == channel.AGENT and message.text == p["arguments"]["body"]
        return ("confirmed" if same else "mismatch"), {**course.effect(p["arguments"]["effect_id"]), "confirmed_message_id": message.id}
    # Independent environment read, not a model assertion or the failed result.
    with course.db() as conn:
        found = conn.execute("SELECT * FROM effects WHERE action_key=?", (p["action_key"],)).fetchone()
    if found is None:
        return "absent", None
    effect = dict(found)
    a = p["arguments"]
    same = (effect["question_id"] == a["question_id"]
            and effect["kind"] == ("reply" if p["tool"] == "course_create_reply" else "flag")
            and (effect["body"] == a["body"] and json.loads(effect["sources"]) == a["source_ids"]
                 if "body" in a else effect["reason"] == a["reason"]))
    return ("confirmed" if same else "mismatch"), effect


def answer(identifier, session_id, trace):
    row = get(identifier)
    if row["status"] not in ACTIVE:
        return "Already resolved; no operation was repeated."
    if state.is_stopped(row["run_id"]):
        return "Run is stopped. The escalation remains held."
    try:
        outcome, effect = inspect(identifier)
    except Exception:
        trace.event("escalation_inspection", escalation_id=identifier, outcome="unknown")
        return "Readback is still unavailable. The run remains held; no write was retried."
    if outcome == "mismatch":
        return "The saved key identifies different content. Staff must investigate; the run remains held."
    status = "resolved" if outcome == "confirmed" else "awaiting_recovery"
    if outcome == "confirmed" and row["payload"]["tool"] == "course_send_reply":
        try:
            effect = course.confirm_agent_send(effect["id"], effect["confirmed_message_id"],
                                               key=row["payload"]["action_key"],
                                               body=row["payload"]["arguments"]["body"])
        except Exception:
            return "Receipt verification failed. The run remains held; no send was retried."
    with db() as conn:
        _schema(conn)
        changed = conn.execute("""UPDATE escalations SET status=?,resolved_at=?,resolved_by=?,resolution=?
          WHERE id=? AND status IN ('held','awaiting_recovery')""",
          (status, now(), session_id, canonical({"outcome": outcome, "effect_id": effect["id"] if effect else None}), identifier)).rowcount
        if changed and outcome == "confirmed" and row["payload"].get("approval_id"):
            conn.execute("UPDATE approvals SET status='executed',outcome=? WHERE id=? AND status='uncertain'",
                         (canonical({"confirmed_effect_id": effect["id"]}), row["payload"]["approval_id"]))
    trace.event("escalation_answer", escalation_id=identifier, control_run_id=row["run_id"],
                answered_by=session_id, outcome=outcome, repeated_call=False)
    if outcome == "absent":
        return "No effect exists under the saved key. Held for Part 1 same-key recovery; no write was retried."
    return f"Confirmed existing effect {effect['id']}; no write was repeated. Remaining task continuation requires Part 1."


def command(session_id, text, trace):
    words = text.strip().split()
    if not words or words[0] not in ("/escalations", "/resolve"):
        return None
    if words[0] == "/resolve":
        if len(words) != 3 or words[2] != "confirm":
            return "Use /resolve <escalation-id> confirm. Confirmation always checks the sandbox."
        return answer(words[1], session_id, trace)
    if len(words) != 1:
        return "Use /escalations to inspect held work."
    rows = records()
    for row in rows:
        trace.event("escalation_opened", escalation_id=row["id"], opened_by=session_id)
    return "\n\n".join(f"{r['id']} ({r['status']}; timeout={r['timed_out']}; over_cap={r['over_cap']})\n"
                          + "\n".join(f"{k}: {v}" for k, v in r["payload"]["packet"].items())
                          for r in rows) or "No escalation is held."
