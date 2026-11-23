"""Long-session end-state, context-budget, compaction and provenance checks."""
from __future__ import annotations

import json

from checks.course import check as course_check
from checks.helpers import connect


def check(run):
    passed, reason, measures = course_check(run)
    if not passed:
        return passed, reason, measures
    events = [json.loads(line) for line in run.trace_path.read_text().splitlines() if line.strip()]
    contexts = [e for e in events if e.get("type") == "context_assembled"]
    if not contexts or any(e.get("estimated_tokens", 999999) > e.get("budget_tokens", 0) for e in contexts):
        return False, "A model call was missing a budget record or exceeded its context budget", measures
    compacted = [e for e in contexts if e.get("compacted")]
    starts = [e for e in events if e.get("type") == "run_start"]
    free_run = not starts or bool(starts[0].get("free"))
    if not compacted and not free_run:
        return False, "The long session never crossed the compaction threshold", measures
    if not any(e.get("type") == "memory_write" and e.get("memory_kind") == "operator_preference" for e in events):
        return False, "The early operator preference was not written with provenance", measures
    if not any(e.get("type") == "memory_read" and e.get("before_model") for e in events):
        return False, "The preference was not read before a later model call", measures
    with connect(run, "memory.sqlite3") as conn:
        row = conn.execute("SELECT source_type,source_id FROM memories WHERE kind='operator_preference' AND name='answer_style' AND superseded_at IS NULL").fetchone()
    if row is None or row[0] != "trusted_operator" or not row[1]:
        return False, "Stored preference provenance is wrong", measures
    replies = "\n".join(r.get("text", "") for r in run.replies)
    if "SYN-Q-session" not in replies:
        return False, "The late follow-up did not identify the earlier session record", measures
    return True, "Long session stayed bounded, retained provenance memory and used correct public facts", {
        **measures, "context_calls": len(contexts), "compactions": len(compacted),
        "max_estimated_tokens": max(e["estimated_tokens"] for e in contexts)}
