"""Measured split candidate: independent evidence and state-audit roles."""
from __future__ import annotations

import json
import uuid

from harness import schema

RETURN_SCHEMA = {
    "type": "object",
    "properties": {
        "result": {"type": "object"},
        "status": {"type": "string", "enum": ["found", "candidate", "out of budget"]},
        "searched": {"type": "array", "items": {"type": "string"}},
        "not_searched": {"type": "array", "items": {"type": "string"}},
        "spent": {"type": "object", "properties": {
            "tool_calls": {"type": "integer", "minimum": 0},
            "tokens": {"type": "integer", "minimum": 0}},
            "required": ["tool_calls", "tokens"], "additionalProperties": False},
        "could_not_determine": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["result", "status", "searched", "not_searched", "spent", "could_not_determine"],
    "additionalProperties": False,
}


class SharedBudget:
    def __init__(self, *, tokens=32000, tool_calls=48):
        self.token_limit = tokens
        self.call_limit = tool_calls
        self.tokens = 0
        self.tool_calls = 0

    def charge_call(self):
        if self.tool_calls >= self.call_limit:
            return False
        self.tool_calls += 1
        return True

    def snapshot(self, start_calls, start_tokens):
        return {"tool_calls": self.tool_calls - start_calls, "tokens": self.tokens - start_tokens}


def validate_return(value):
    errors = schema.errors(value, RETURN_SCHEMA)
    if errors:
        raise ValueError("Invalid role return: " + "; ".join(errors)[:400])
    return value


def _call(registry, budget, name, arguments):
    if not budget.charge_call():
        return None
    result = registry.call(name, arguments, caller="workflow")
    if result.is_error:
        raise ValueError(result.data.get("error", "role tool failed"))
    return result.data


def evidence_role(registry, question_ids, budget):
    start = budget.tool_calls, budget.tokens
    found, searched, missing = {}, [], []
    for qid in question_ids:
        question = _call(registry, budget, "course_get_question", {"question_id": qid})
        if question is None:
            missing.append(qid)
            continue
        topic = question["question"].get("topic")
        searched.append(qid)
        if not topic:
            found[qid] = {"topic": None, "documents": []}
            continue
        matches = _call(registry, budget, "course_search_materials", {"query": topic})
        documents = []
        for match in (matches or {}).get("documents", []):
            document = _call(registry, budget, "course_read_document", {"document_id": match["id"]})
            if document:
                documents.append(document["document"]["id"])
        found[qid] = {"topic": topic, "documents": documents}
    return validate_return({"result": found, "status": "out of budget" if missing else "found",
        "searched": searched, "not_searched": missing,
        "spent": budget.snapshot(*start), "could_not_determine": list(missing)})


def audit_role(registry, question_ids, budget):
    start = budget.tool_calls, budget.tokens
    result, searched, missing = {}, [], []
    for qid in question_ids:
        status = _call(registry, budget, "course_status", {"question_id": qid})
        if status is None:
            missing.append(qid)
            continue
        searched.append(qid)
        result[qid] = {"preexisting_effects": len(status["effects"]), "write_surface": "registry_only"}
    return validate_return({"result": result, "status": "out of budget" if missing else "candidate",
        "searched": searched, "not_searched": missing,
        "spent": budget.snapshot(*start), "could_not_determine": list(missing)})


def run_candidate(registry, question_ids, trace, *, parent_id=None, budget=None,
                  roles=(evidence_role, audit_role)):
    """Run independent read-only roles; coordinator remains the only writer."""
    parent_id = parent_id or "topology-" + uuid.uuid4().hex[:12]
    budget = budget or SharedBudget()
    returns = []
    for role in roles:
        role_id = parent_id + ":" + role.__name__
        trace.event("topology_agent_start", parent_id=parent_id, agent_id=role_id,
                    role=role.__name__, waits_on=[])
        value = validate_return(role(registry, question_ids, budget))
        trace.event("topology_agent_end", parent_id=parent_id, agent_id=role_id,
                    role=role.__name__, status=value["status"], spent=value["spent"],
                    waits_on=[], return_contract=value)
        returns.append(value)
    trace.event("topology_budget", parent_id=parent_id, tokens=budget.tokens,
                tool_calls=budget.tool_calls, token_limit=budget.token_limit,
                tool_call_limit=budget.call_limit)
    return returns


def combined_end_state(question_ids, effects):
    """Only sandbox state decides success; role self-reports cannot override it."""
    counts = {qid: 0 for qid in question_ids}
    for effect in effects:
        if effect.get("question_id") in counts and effect.get("status") not in ("discarded", "cleared"):
            counts[effect["question_id"]] += 1
    errors = [f"{qid}: expected one active effect, found {count}" for qid, count in counts.items() if count != 1]
    return {"passed": not errors, "errors": errors, "counts": counts}
