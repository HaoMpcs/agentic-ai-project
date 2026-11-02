"""Shared course data and persistent effects. All paths resolve at call time."""
from __future__ import annotations

import contextlib
import hashlib
import json
import re
import sqlite3
import threading

import channel
from harness import runtime
from harness.paths import state_dir

_send_lock = threading.Lock()
KINDS = ("deadline", "office_hours", "conceptual", "repeated", "personal", "exception", "unauthorized", "ambiguous")
FLAG_REASONS = ("private_request", "staff_decision", "missing_information", "conflicting_sources")
REFUSAL = "I cannot share another student's private information or work. Please contact course staff about your own question."


def stamp() -> str:
    run = runtime.current_run()
    return run.run_id if run else (runtime.current_session() or "manual")


@contextlib.contextmanager
def db():
    conn = sqlite3.connect(state_dir() / "course.sqlite3", timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, data TEXT NOT NULL, stamp TEXT NOT NULL,
          PRIMARY KEY(kind,id));
        CREATE TABLE IF NOT EXISTS effects (id TEXT PRIMARY KEY, kind TEXT NOT NULL, question_id TEXT NOT NULL,
          body TEXT NOT NULL, sources TEXT NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL,
          stamp TEXT NOT NULL, updated_by TEXT NOT NULL, action_key TEXT NOT NULL UNIQUE, channel_id INTEGER);
        CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, effect_id TEXT, action TEXT, note TEXT,
          stamp TEXT NOT NULL);
        """)
        with conn:
            yield conn
    finally:
        conn.close()


def put_record(kind: str, item: dict) -> None:
    if not str(item.get("id", "")).startswith("SYN-"):
        raise ValueError("synthetic records need a SYN- identifier")
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO records VALUES (?,?,?,?)",
                     (kind, item["id"], json.dumps(item), stamp()))


def records(kind: str) -> list[dict]:
    with db() as conn:
        return [json.loads(r[0]) for r in conn.execute("SELECT data FROM records WHERE kind=? ORDER BY id", (kind,))]


def record(kind: str, identifier: str) -> dict:
    with db() as conn:
        row = conn.execute("SELECT data FROM records WHERE kind=? AND id=?", (kind, identifier)).fetchone()
    if row is None:
        raise ValueError(f"No {kind} record {identifier}; use an identifier returned by a course read.")
    return json.loads(row[0])


def question(identifier: str) -> dict:
    item = record("question", identifier)
    messages = [m for m in channel.messages(identifier) if m.from_outside]
    return {**item, "untrusted_messages": [m.text[:4000] for m in messages[-3:]]}


def materials(query: str) -> list[dict]:
    words = set(re.findall(r"[a-z0-9]+", query.lower()))
    found = []
    for item in records("document"):
        haystack = set(re.findall(r"[a-z0-9]+", f"{item['topic']} {item['title']}".lower()))
        if item["active"] and words & haystack:
            found.append({k: item[k] for k in ("id", "title", "topic", "version", "active")})
    exact = [x for x in found if x["topic"].lower() == query.lower()]
    return (exact or found)[:6]


def public_answers(topic: str) -> list[dict]:
    return [x for x in records("public_answer") if x["topic"] == topic][:4]


def conflicting_documents(documents: list[dict]) -> bool:
    """Versioned structured claims with the same semantic key must agree."""
    values = {}
    for document in documents:
        for key, value in document.get("claims", {}).items():
            values.setdefault(key, set()).add(json.dumps(value, sort_keys=True))
    return any(len(items) > 1 for items in values.values())


def _effect(row) -> dict:
    result = dict(row)
    result["source_ids"] = json.loads(result.pop("sources"))
    return result


def effects(*, run_id: str | None = None, question_id: str | None = None) -> list[dict]:
    query, args = "SELECT * FROM effects WHERE 1=1", []
    for field, value in (("stamp", run_id), ("question_id", question_id)):
        if value is not None:
            query += f" AND {field}=?"
            args.append(value)
    with db() as conn:
        return [_effect(r) for r in conn.execute(query + " ORDER BY id", args)]


def effect(identifier: str) -> dict:
    with db() as conn:
        row = conn.execute("SELECT * FROM effects WHERE id=?", (identifier,)).fetchone()
    if row is None:
        raise ValueError("No such draft or flag.")
    return _effect(row)


def create_effect(kind: str, question_id: str, *, body: str = "", source_ids: list | None = None,
                  reason: str = "", key: str) -> dict:
    record("question", question_id)
    if kind not in ("reply", "flag"):
        raise ValueError("Effect kind must be reply or flag.")
    if kind == "flag" and reason not in FLAG_REASONS:
        raise ValueError(f"Use a flag reason in {FLAG_REASONS}.")
    if kind == "reply" and (not body.strip() or len(body) > 2500):
        raise ValueError("A draft must contain 1–2500 characters.")
    identifier = "SYN-" + kind.upper() + "-" + hashlib.sha256(key.encode()).hexdigest()[:16]
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO effects VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
                     (identifier, kind, question_id, body, json.dumps(source_ids or []), reason,
                      "pending" if kind == "reply" else "open", stamp(), stamp(), key))
        row = conn.execute("SELECT * FROM effects WHERE action_key=?", (key,)).fetchone()
    return _effect(row)


def manual_draft(question_id: str, body: str, source_ids: list[str]) -> dict:
    question_item = record("question", question_id)
    for identifier in source_ids:
        document = record("document", identifier)
        if (not document["active"] or document["visibility"] != "public"
                or document["topic"] != question_item["topic"]):
            raise ValueError("Choose active public sources matching the question topic.")
    previous = effects(question_id=question_id)
    serial = sum(x["stamp"] == "manual" and x["kind"] == "reply" for x in previous)
    if any(x["status"] == "pending" for x in previous):
        raise ValueError("A pending draft already exists; review or discard it first.")
    return create_effect("reply", question_id, body=body, source_ids=source_ids,
                         key=f"manual:reply:{question_id}:{serial}")


def update_status(identifier: str, status: str, note: str = "") -> dict:
    item = effect(identifier)
    valid = {"reply": {"pending": {"discarded"}, "discarded": {"pending"}},
             "flag": {"open": {"cleared"}, "cleared": {"open"}}}
    if status not in valid[item["kind"]].get(item["status"], set()):
        raise ValueError("That status transition is not allowed.")
    with db() as conn:
        conn.execute("UPDATE effects SET status=?, updated_by=? WHERE id=? AND status=?",
                     (status, stamp(), identifier, item["status"]))
        conn.execute("INSERT INTO audit(effect_id,action,note,stamp) VALUES (?,?,?,?)",
                     (identifier, status, note[:500], stamp()))
    return effect(identifier)


def send_pending(identifier: str) -> dict:
    """Operator-only send. Claim before sending; an uncertain send is never retried."""
    with _send_lock:
        item = effect(identifier)
        if item["status"] == "sent":
            return item
        if item["kind"] != "reply" or item["status"] != "pending":
            raise ValueError("Only a pending reply can be sent. Inspect uncertain sends in Threads.")
        with db() as conn:
            changed = conn.execute("UPDATE effects SET status='sending', updated_by=? WHERE id=? AND status='pending'",
                                   (stamp(), identifier)).rowcount
        if changed != 1:
            raise ValueError("Another operator claimed this draft; refresh its status.")
        try:
            message = channel.send(item["question_id"], item["body"], sender="operator")
        except Exception:
            with db() as conn:
                conn.execute("UPDATE effects SET status='uncertain' WHERE id=?", (identifier,))
            raise ValueError("Send uncertain. Staff must inspect Threads before taking further action.") from None
        with db() as conn:
            conn.execute("UPDATE effects SET status='sent', channel_id=? WHERE id=?", (message.id, identifier))
            conn.execute("INSERT INTO audit(effect_id,action,note,stamp) VALUES (?,?,?,?)",
                         (identifier, "sent", str(message.id), stamp()))
        return effect(identifier)
