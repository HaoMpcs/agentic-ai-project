# M2 Part A: runtime handoff

Owner: Jingyu Huang (CNetID: jyhuang28). Scope: runtime, recovery, MCP,
tool loading, restricted code calls and the outside exchange. This document
defines integration contracts, not implementations of Parts B or C.

## Stable entry points

The app and runner still enter through `agent/service.py`. Do not import other
agent modules into app pages. `harness/`, `channel/` and `run.py` are unchanged.

| Entry | Contract |
|---|---|
| `operator_turn(session_id, text)` | Starts work, reads persisted follow-up selection, or accepts `resume` for the session's live run. |
| `on_outside_reply(thread_id, text)` | Resumes only a matching durable external wait. The harness has already stored the message. Outside text never executes operator commands. |
| `resume_run(run_key)` | Call-triggered resume; no startup supervisor. Held/stopped runs must first be explicitly released by C. |
| `compensate_run(run_key)` | Operator-only reverse-order compensation through Registry/MCP. C authorizes the command; ordinary work remains stopped. Irreversible messages report `none`. |

## Run identity and persistence

`sandbox.execution.create` allocates a run number transactionally. The key is
`<runner run_id>:<number>` in tests/runner, or `<console session_id>:<number>` in
the app. Effects retain the harness-required run/session stamp. Keys for logical
effects use the narrower run key. Never derive a new run ID in B or C.

`sandbox.execution.load/latest/history/calls/live_runs` read the SQLite runtime store.
Use `live_runs()` for C's queue and B's startup inventory of unfinished runs.
The durable record contains request, selected question IDs, route, selected
plan/code mode, status, wait and snapshot. The snapshot includes a validated
plan/prefix, pending model tool calls and exact arguments, messages, operational
read capabilities, critique state and cumulative bounds. Completed call records
also contain their keys and results. `run_checkpoint` trace events materialize
the record and journal so they remain inspectable after sandbox reset.

Statuses: `running`, `waiting_external`, `held`, `stopped`, `completed`, `failed`,
`cancelled`. There is one live external wait per thread. Process/thread ownership
prevents simultaneous replay; a dead process can be replaced on the next call.

## Part B adapter

Implement the body of `agent.execution.assemble_context` or delegate from that
function to a B-owned module. Signature:

```python
assemble_context(*, system, messages, tools, purpose) -> {
    "system": str, "messages": list, "tools": list | None
}
```

Every `Bounds.model` call uses it, including planner, reviser, investigation and
code generation. It currently returns candidates unchanged: context budget,
notes, compaction and memory are B's work. For `plan` and `revise_plan`, do not
introduce outside text or notes. Tool definitions must count toward the budget.
The existing per-task 32,000-token bound is not a per-call context budget.

`agent.execution.current()` exposes the active execution. Read `data` for run
metadata and use `save(**snapshot_fields)` for serializable B-owned run state.
Cross-session memory belongs in a separate B-owned sandbox module, not here.
`tool_offering` events record names and definition characters on every model
call. B must add the selected context/window budget and role-specific accounting.

## Part C adapters

* `agent.execution.policy_check(name, arguments)` is called by Registry before
  dispatch. It currently enforces the durable hold/stop and existing M1 scopes;
  it does not implement the three-column policy. Return exactly `True` to allow.
  Ordinary hook exceptions fail closed. To pause, persist the reason and raise
  `Halt("run_held", ...)` rather than allowing a call.
* `agent.execution.operator_control(session_id, text)` runs before the ordinary
  session lock. It currently returns `None`. C parses stop/cancel/resume/rollback,
  limits and mid-task messages here and returns a `Reply` when handled.
* `agent.execution.before_model_call(system=..., messages=..., tools=..., purpose=...)`
  runs before B's assembler. C consumes its persisted trusted-message queue here;
  return the same three model-input fields or raise `Halt` after saving a hold.
  Do not route outside text through this privileged operator-message path.
* `hold(run_key, reason, stopped=False)` persists a hold; `release_hold(run_key)`
  explicitly clears one. A stale execution snapshot cannot overwrite it.
* `compensate_run` sets an internal `command="rollback"` capability for the
  trusted operator operation, including a replaced/cancelled old run. Registry
  permits only compensation calls in that context and still invokes C's hook;
  model calls are refused. C must authorize this command before calling it and
  distinguish it from resuming ordinary work when evaluating the stop flag.
* Fill the existing approval service functions and approval/queue pages. Resolve
  a pending item to its persisted run key, then call `resume_run`.
* A sends only a code-written public-topic question. Its disclosure is in
  `sandbox.exchange.clarification_text`. C should consolidate all future agent
  sends into its common disclosure/policy path, preserving this line and the
  dry-run text. The model cannot choose this question's body or action key.

No answer on the outside channel releases a hold or grants approval. Do not
resume a held run merely because a reply arrived. C must keep approval and
escalation state durable and arrange any operator-authorized rollback through
the same hook; A does not supply those policy decisions.

## Shared-file ownership and verification

Prefer B/C-owned modules and small delegating changes at the adapter points.
Coordinate changes to `service.py`, `tools.py`, `bounds.py`, `planning.py`, seed,
switches and requirements. Each new switch needs its own `added` date.
The current executor has one coordinator. A process/thread lease prevents
concurrent resumes; it does not make a shared Python execution object a parallel
worker store. B must serialize Registry access or add a tested atomic dispatcher
when its topology actually runs workers concurrently.

Run `make test`, `make check`, and the Part A analysis command in README.
`tests/test_m2_runtime.py` includes real SDK dispatch, process-kill recovery,
channel-gap recovery, policy rejection, code confinement and adapter tests.
These free mechanism tests are not the M2 baseline or either improvement pass.
After B/C integration, the team must run all tasks, including sessions, and the
two sequential pilot passes with advance-pushed predictions.
