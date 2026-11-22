"""One deterministic builder for agent-authored outgoing messages, before gating."""
from __future__ import annotations

from agent.critique import validate_draft
from sandbox import course

LINE = "This message was written by an automated AI agent. To reach a person, reply here and ask for the course TA."


def render(body: str) -> str:
    if not isinstance(body, str) or not body.strip():
        raise ValueError("An outgoing message needs a nonempty body.")
    if body.endswith("\n\n" + LINE) and body.count(LINE) == 1:
        return body
    if LINE in body:
        raise ValueError("The disclosure must appear once, as the final separate paragraph.")
    return body.rstrip() + "\n\n" + LINE


def valid(body):
    return isinstance(body, str) and body.endswith("\n\n" + LINE) and body.count(LINE) == 1


def prepare(effect_id):
    effect = course.effect(effect_id)
    if effect["kind"] != "reply" or effect["status"] != "pending":
        raise ValueError("Select a pending reply draft; inspect sent/uncertain items in Threads.")
    if course.draft_author(effect_id) != "automated":
        raise ValueError("Select an automated draft with recorded authorship; send human-written messages manually.")
    passed, reason = validate_draft(effect["question_id"], effect["body"], effect["source_ids"])
    if not passed:
        raise ValueError("Draft cannot be sent automatically: " + reason)
    return {"question_id": effect["question_id"], "effect_id": effect_id, "body": render(effect["body"])}
