# Milestone 2 Part A contributions: Jingyu Huang (CNetID: jyhuang28).
"""Externally enforced per-task model/tool bounds, distinct from harness ceiling."""
from __future__ import annotations

import queue
import json
import threading
import time

from harness import runtime
from policy import controls, state as policy_state

MAX_STEPS = 24
TOKEN_BUDGET = 32000
WALL_SECONDS = 45.0
_inflight = {}
_guard = threading.Lock()


class Halt(Exception):
    def __init__(self, reason, detail=""):
        self.reason, self.detail = reason, detail
        super().__init__(detail or reason)


class Bounds:
    def __init__(self, session_id, *, run_id=None):
        from agent import execution
        self.execution = execution.current()
        previous = self.execution.data["snapshot"].get("bounds", {}) if self.execution else {}
        self.session_id = session_id
        run = runtime.current_run()
        self.control_run_id = run_id or (run.run_id if run else session_id)
        self.trace = runtime.trace(session_id)
        self.started = time.monotonic()
        self.steps = previous.get("steps", 0)
        self.previous_tokens = previous.get("tokens", 0)
        self.previous_elapsed = previous.get("elapsed_s", 0)
        self.client = None
        self.initial_tokens = 0
        self.trace.event("agent_bounds", max_steps=MAX_STEPS, token_budget=TOKEN_BUDGET,
                         wall_seconds=WALL_SECONDS, harness_ceiling_separate=True, control_run_id=self.control_run_id)

    def check(self):
        if policy_state.is_stopped(self.control_run_id):
            controls.observe(self.control_run_id, self.trace)
            raise Halt("run_stopped", "Operator interrupted the run; no further model or tool calls permitted.")
        if self.execution:
            if self.execution.command == "rollback":
                raise Halt("operator_only", "Rollback never calls a model or resumes the agent.")
            self.execution.check()
        if self.previous_elapsed + time.monotonic() - self.started >= WALL_SECONDS:
            raise Halt("agent_wall_clock", "Wall-clock boundary; no further tools or effects permitted.")
        if self.previous_tokens + (self.client.total_tokens - self.initial_tokens if self.client else 0) >= TOKEN_BUDGET:
            raise Halt("agent_token_budget", "Agent token boundary; distinct from the harness token_budget ceiling.")

    def save(self):
        if self.execution:
            self.execution.save(bounds={"steps": self.steps,
                "tokens": self.previous_tokens + (self.client.total_tokens - self.initial_tokens if self.client else 0),
                "elapsed_s": self.previous_elapsed + time.monotonic() - self.started})

    def tick(self):
        self.check()
        if self.steps >= MAX_STEPS:
            raise Halt("agent_step_limit")
        self.steps += 1
        self.save()

    def model(self, *, system, messages, tools=None, purpose="execute"):
        from policy import messages as inbox
        inbox.observe(self.control_run_id, self.trace, messages)
        from agent import execution
        controlled = execution.before_model_call(system=system, messages=messages, tools=tools, purpose=purpose)
        assembled = execution.assemble_context(**controlled, purpose=purpose)
        system, messages, tools = assembled["system"], assembled["messages"], assembled["tools"]
        self.trace.event("tool_offering", purpose=purpose, names=[t["name"] for t in tools or []],
                         definition_characters=len(json.dumps(tools or [])))
        self.tick()
        if self.client is None:
            self.client = runtime.client(self.session_id)
            self.initial_tokens = self.client.total_tokens
        self.trace.progress(f"{purpose}: model call {self.steps}; outgoing replies remain pending staff review.")
        answers = queue.Queue(maxsize=1)
        client = self.client
        with _guard:
            previous = _inflight.get(id(client))
            if previous is not None and previous.is_alive():
                raise Halt("model_still_inflight", "A previous provider request is still running; wait before retrying this session.")
        # The worker only calls the metered model. It cannot execute a tool or
        # write a sandbox effect. A hung SDK therefore cannot hold the operator
        # past the task deadline. A late provider charge needs reconciliation.
        def request():
            try:
                answers.put((True, client.create(system=system, messages=messages, tools=tools)))
            except Exception as exc:
                answers.put((False, exc))
        worker = threading.Thread(target=request, daemon=True)
        with _guard:
            _inflight[id(client)] = worker
        worker.start()
        while True:
            remaining = WALL_SECONDS - self.previous_elapsed - (time.monotonic() - self.started)
            if remaining <= 0:
                self.trace.event("model_inflight_timeout", billing="unknown until provider returns; no tools executed by worker")
                raise Halt("agent_wall_clock", "Provider still in flight; inspect billing before measurements.")
            try:
                ok, response = answers.get(timeout=min(0.1, remaining))
                break
            except queue.Empty:
                try:
                    self.check()
                except Halt as exc:
                    if exc.reason == "run_stopped":
                        self.trace.event("model_interrupted_inflight", billing="unknown until provider returns; worker cannot execute tools")
                    raise
        if not ok:
            raise response
        self.trace.model_call(self.steps, response, purpose=purpose, content=response.content, control_run_id=self.control_run_id)
        self.save()
        self.check()  # never dispatch tool calls from a response over the boundary
        return response
