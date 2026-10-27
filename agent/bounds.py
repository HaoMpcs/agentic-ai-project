"""Externally enforced per-task model/tool bounds, distinct from harness ceiling."""
from __future__ import annotations

import queue
import threading
import time

from harness import runtime

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
    def __init__(self, session_id):
        self.session_id = session_id
        self.trace = runtime.trace(session_id)
        self.started = time.monotonic()
        self.steps = 0
        self.client = None
        self.initial_tokens = 0
        self.trace.event("agent_bounds", max_steps=MAX_STEPS, token_budget=TOKEN_BUDGET,
                         wall_seconds=WALL_SECONDS, harness_ceiling_separate=True)

    def check(self):
        if time.monotonic() - self.started >= WALL_SECONDS:
            raise Halt("agent_wall_clock", "Wall-clock boundary; no further tools or effects permitted.")
        if self.client and self.client.total_tokens - self.initial_tokens >= TOKEN_BUDGET:
            raise Halt("agent_token_budget", "Agent token boundary; distinct from the harness token_budget ceiling.")

    def tick(self):
        self.check()
        if self.steps >= MAX_STEPS:
            raise Halt("agent_step_limit")
        self.steps += 1

    def model(self, *, system, messages, tools=None, purpose="execute"):
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
            remaining = WALL_SECONDS - (time.monotonic() - self.started)
            if remaining <= 0:
                self.trace.event("model_inflight_timeout", billing="unknown until provider returns; no tools executed by worker")
                raise Halt("agent_wall_clock", "Provider still in flight; inspect billing before measurements.")
            try:
                ok, response = answers.get(timeout=min(5.0, remaining))
                break
            except queue.Empty:
                self.trace.progress(f"{purpose}: still waiting for the provider; {max(0, int(remaining - 5))} seconds remain.")
        if not ok:
            raise response
        self.trace.model_call(self.steps, response, purpose=purpose, content=response.content)
        self.check()  # never dispatch tool calls from a response over the boundary
        return response
