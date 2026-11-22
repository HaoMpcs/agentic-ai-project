# Author: Jingyu Huang (CNetID: jyhuang28).
"""Run-scoped persistence and explicit extension points for parts B and C."""
from __future__ import annotations

import contextlib
import contextvars
import copy
import json
import re

from harness import runtime
from sandbox import execution as store
from agent.bounds import Halt

_active = contextvars.ContextVar("active_execution", default=None)


def current():
    return _active.get()


class Execution:
    def __init__(self, data):
        self.data = data
        self.trace = runtime.trace(data["session_id"])
        self.cursor = data["snapshot"].get("cursor", 0)
        self.command = None

    @property
    def key(self):
        return self.data["run_key"]

    def save(self, **snapshot):
        self.data["snapshot"].update(copy.deepcopy(snapshot))
        registry = getattr(self, "registry", None)
        if registry is not None:
            self.data["snapshot"]["registry"] = {
                "read_questions": sorted(registry.read_questions), "read_docs": sorted(registry.read_docs),
                "critique_rounds": registry.critique_rounds, "previous_drafts": registry.previous_drafts}
        store.save(self.data, preserve_control=True)

    def check(self):
        if self.command == "rollback":
            return
        saved = store.load(self.key)
        if saved["stop"] or saved["status"] in ("held", "stopped", "cancelled"):
            raise Halt("run_held", "Run is held; an explicit operator resume is required.")

    def finish(self, status, reason):
        self.data.update(status=status, end_reason=reason)
        self.save()
        self.emit_checkpoint()

    def emit_checkpoint(self):
        checkpoint = {**self.data, "calls": store.calls(self.key)}
        self.trace.event("run_checkpoint", checkpoint=checkpoint, final=True)


@contextlib.contextmanager
def activate(data):
    store.claim(data["run_key"])
    execution = Execution(data)
    token = _active.set(execution)
    try:
        yield execution
    finally:
        # A live turn may have been interrupted by C through the store.
        _active.reset(token)
        store.release(execution.key)


def hold(run_key, reason, *, stopped=False):
    """C owns the decision to hold; A supplies the durable operation."""
    data = store.control(run_key, status="stopped" if stopped else "held", stop=stopped, reason=reason)
    runtime.trace(data["session_id"]).event("run_held", run_key=run_key, reason=reason)


def release_hold(run_key):
    return store.control(run_key, status="running", stop=False, releasing=True)


def assemble_context(*, system, messages, tools, purpose):
    """Fit every request to a deterministic budget, retaining atomic call pairs."""
    active = current()
    budget = 12000
    threshold = 9000
    tool_chars = len(json.dumps(tools or [], sort_keys=True))
    system_chars = len(system)
    limit_chars = max(1200, budget * 4 - tool_chars - system_chars)
    prepared = copy.deepcopy(messages)
    from sandbox import memory
    records = memory.prompt_records()
    if records and purpose not in ("plan", "revise_plan"):
        prepared.insert(0, {"role": "user", "content": json.dumps({"confirmed_operator_memory": records}, sort_keys=True)})
        if active:
            active.trace.event("memory_read", run_key=active.key, records=len(records), before_model=True)
    original_chars = len(json.dumps(prepared, sort_keys=True))
    notes = []
    omitted = 0
    while len(json.dumps(prepared, sort_keys=True)) > limit_chars and len(prepared) > 2:
        item = prepared.pop(0)
        text = str(item.get("content", ""))
        # Notes accept only trusted operator selections, never outside/student text
        # and never planner inputs.
        if purpose not in ("plan", "revise_plan") and "trusted_operator" in text and not re.search(
                r"untrusted|student_messages|outside", text, re.I):
            notes.append(text[:300])
        omitted += 1
    if notes:
        prepared.insert(0, {"role": "user", "content": json.dumps({"durable_notes": notes}, sort_keys=True)})
    if len(json.dumps(prepared, sort_keys=True)) > limit_chars:
        last = copy.deepcopy(prepared[-1])
        last["content"] = str(last.get("content", ""))[-max(500, limit_chars // 2):]
        prepared = [last]
    estimated = (system_chars + tool_chars + len(json.dumps(prepared, sort_keys=True)) + 3) // 4
    if active:
        active.save(context={"budget_tokens": budget, "estimated_tokens": estimated,
                             "omitted_messages": omitted, "notes": notes})
        active.trace.event("context_assembled", purpose=purpose, budget_tokens=budget,
                           estimated_tokens=estimated, original_characters=original_chars,
                           omitted_messages=omitted, compacted=original_chars > threshold * 4,
                           notes_count=len(notes), tool_characters=tool_chars)
    return {"system": system, "messages": prepared, "tools": tools}


def before_model_call(*, system, messages, tools, purpose):
    """C consumes trusted mid-task messages here, before B assembles context."""
    active = current()
    if active:
        active.check()
    return {"system": system, "messages": messages, "tools": tools}


def operator_control(session_id, text):
    """C can handle urgent commands before the ordinary session lock/queue."""
    match = re.fullmatch(r"/remember\s+preference\s+([A-Za-z0-9_-]{1,40})\s+(.{1,500})", text.strip())
    if match:
        from sandbox import memory
        from harness.turns import Reply
        row = memory.put("operator_preference", match.group(1), match.group(2),
                         source_type="trusted_operator", source_id=session_id)
        runtime.trace(session_id).event("memory_write", memory_kind=row["kind"], name=row["name"],
                                        provenance={"source_type": row["source_type"], "source_id": row["source_id"]})
        return Reply(f"Remembered operator preference {row['name']} with provenance.")
    return None


class Waiting(Exception):
    def __init__(self, thread_id):
        self.thread_id = thread_id


def policy_check(name, arguments):
    """Deployment veto hook; Registry performs the mandatory policy first."""
    return True
