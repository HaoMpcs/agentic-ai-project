"""Durable per-action approvals, independent of the Part 1 task checkpoint.

Only the trusted service decides; the registry creates immutable requests and
rechecks policy at execution. No model-supplied approval argument is accepted.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

import channel
from agent.critique import validate_draft
from harness import runtime
from harness.trace import now
from policy import state
from policy.state import db
from sandbox import course


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS approvals (
      id TEXT PRIMARY KEY, session_id TEXT NOT NULL, run_id TEXT NOT NULL,
      status TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL,
      decided_at TEXT, decided_by TEXT, approved INTEGER, note TEXT,
      elapsed_s REAL, outcome TEXT)""")


def _row(row):
    if row is None:
        raise ValueError("No such approval request.")
    result = dict(row)
    result["payload"] = json.loads(result["payload"])
    result["outcome"] = json.loads(result["outcome"]) if result["outcome"] else None
    return result


def get(identifier):
    with db() as conn:
        _schema(conn)
        return _row(conn.execute("SELECT * FROM approvals WHERE id=?", (identifier,)).fetchone())


def records(statuses=("pending",)):
    with db() as conn:
        _schema(conn)
        rows = conn.execute("SELECT * FROM approvals ORDER BY created_at,id").fetchall()
    return [_row(r) for r in rows if r["status"] in statuses]


def reset():
    with db() as conn:
        _schema(conn)
        conn.execute("DELETE FROM approvals")


def current_facts(args):
    question = course.record("question", args["question_id"])
    effect = course.effect(args["effect_id"]) if "effect_id" in args else None
    ids = effect["source_ids"] if effect else args.get("source_ids", [])
    documents = [course.record("document", identifier) for identifier in ids]
    return {"question": question, "documents": documents, "selected_effect": effect,
            "draft_authorship": course.draft_author(effect["id"]) if effect else None,
            "student_messages": [m.as_dict() for m in channel.messages(args["question_id"]) if m.from_outside]}


def screen(name, args, facts):
    q = facts["question"]
    docs = facts["documents"]
    sending = name == "course_send_reply"
    effect = facts["selected_effect"]
    passed, explanation = (validate_draft(args["question_id"], effect["body"] if sending else args["body"],
                                         effect["source_ids"] if sending else args["source_ids"])
                           if name in ("course_create_reply", "course_send_reply") else (True, "Categorical staff flag; no message is sent."))
    return {
        "effect": {"tool": name, "arguments": args, "status_after": "sent" if sending else "pending" if name == "course_create_reply" else "open",
                   "publishes_to_student": sending},
        "facts": {"question_id": q["id"], "question_kind": q["kind"], "topic": q["topic"],
                  "target_origin": "existing synthetic question record",
                  "input_author": "outside student; untrusted",
                  "records_changed": 1, "external_recipients": 1 if sending else 0,
                  "recipient_thread": q["id"] if sending else None,
                  "draft_created_by": effect["stamp"] if effect else None,
                  "source_ids": [d["id"] for d in docs],
                  "sources_active_public": all(d.get("active") and d.get("visibility") == "public" for d in docs),
                  "private_marker_present": "SYN-PRIVATE-" in args.get("body", ""),
                  "source_check_passed": passed, "source_check_detail": explanation},
        "student_messages": [{"author": m["sender"], "text": m["text"]} for m in facts["student_messages"]],
        "labels": {"effect": "computed", "facts": "computed", "student_messages": "outside text, untrusted"},
    }


def request(registry, name, args, *, caller, action_class, step=0, plan_step=None, call_id=None):
    facts = current_facts(args)
    payload = {"tool": name, "arguments": args, "action_class": action_class,
               "action_key": registry.key(name, args), "caller": caller,
               "allowed_questions": sorted(registry.allowed), "read_questions": sorted(registry.read_questions),
               "send_effect_ids": sorted(registry.send_effect_ids),
               "read_documents": sorted(registry.read_docs), "facts_digest": digest(facts),
               "screen": screen(name, args, facts), "approval_mode": "per_action",
               "operator_limits": state.limits(registry.session_id),
               "step": step, "plan_step": plan_step, "call_id": call_id,
               "parent_run_id": runtime.current_run().run_id if runtime.current_run() else None,
               "switches": runtime.switches()}
    identifier = "approval-" + digest([registry.session_id, registry.control_run_id, payload])[:24]
    with db() as conn:
        _schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        stopped = conn.execute("SELECT stopped FROM stops WHERE run_id=?", (registry.control_run_id,)).fetchone()
        if stopped and stopped[0]:
            raise PermissionError("Run stopped before approval preparation completed.")
        inserted = conn.execute("INSERT OR IGNORE INTO approvals(id,session_id,run_id,status,created_at,payload) VALUES (?,?,?,'pending',?,?)",
                                (identifier, registry.session_id, registry.control_run_id, now(), canonical(payload))).rowcount
    if get(identifier)["status"] != "pending":
        raise PermissionError("This exact action was already decided; it cannot be silently requested again.")
    if inserted:
        registry.trace.event("approval_requested", approval_id=identifier, action_class=action_class,
                             control_run_id=registry.control_run_id, action_key=payload["action_key"],
                             approval_mode="per_action", screen=payload["screen"], switches=payload["switches"])
    return identifier


def authorizes(identifier, *, session_id, run_id, name, args):
    if not identifier:
        return False
    row = get(identifier)
    p = row["payload"]
    return (row["status"] == "executing" and row["approved"] == 1
            and row["session_id"] == session_id and row["run_id"] == run_id
            and p["tool"] == name and canonical(p["arguments"]) == canonical(args)
            and p["operator_limits"] == state.limits(session_id)
            and p["facts_digest"] == digest(current_facts(args)))


def claim(identifier, approved, note):
    row = get(identifier)
    at = now()
    seconds = max(0.0, (datetime.fromisoformat(at) - datetime.fromisoformat(row["created_at"])).total_seconds())
    actor = "scripted_operator" if runtime.current_run() else "operator"
    with db() as conn:
        _schema(conn)
        changed = conn.execute("""UPDATE approvals SET status=?,decided_at=?,decided_by=?,approved=?,note=?,elapsed_s=?
          WHERE id=? AND status='pending'""",
          ("executing" if approved else "denied", at, actor, int(approved), note[:1000], seconds, identifier)).rowcount
    return get(identifier), bool(changed)


def finish(identifier, status, outcome):
    if status not in ("executed", "blocked", "failed", "uncertain"):
        raise ValueError("Invalid approval execution outcome.")
    with db() as conn:
        _schema(conn)
        conn.execute("UPDATE approvals SET status=?,outcome=? WHERE id=? AND status='executing'",
                     (status, canonical(outcome), identifier))


def pending():
    return [{"id": r["id"], "session_id": r["session_id"], "run_id": r["run_id"],
             "summary": f"{r['payload']['tool']} for {r['payload']['arguments']['question_id']}",
             "created_at": r["created_at"], "screen": r["payload"]["screen"]}
            for r in records()]
