# Author: Jingyu Huang (CNetID: jyhuang28).
"""Run-scoped persistence and explicit extension points for parts B and C."""
from __future__ import annotations

import contextlib
import contextvars
import copy

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
    """B replaces this adapter; no notes, memory or compaction are implemented here."""
    return {"system": system, "messages": messages, "tools": tools}


def before_model_call(*, system, messages, tools, purpose):
    """C consumes trusted mid-task messages here, before B assembles context."""
    active = current()
    if active:
        active.check()
    return {"system": system, "messages": messages, "tools": tools}


def operator_control(session_id, text):
    """C can handle urgent commands before the ordinary session lock/queue."""
    return None


class Waiting(Exception):
    def __init__(self, thread_id):
        self.thread_id = thread_id


def policy_check(name, arguments):
    """C installs classification/approval here. Existing M1 scopes still apply."""
    execution = current()
    if execution:
        execution.check()
    return True
