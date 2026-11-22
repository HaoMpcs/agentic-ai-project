# Part 2: stop, cancel, resume and rollback

Owner: Yani Wu. Updated November 22, 2026 (America/New_York). Source: saved M2 Part 2 task 6 and the local implementation.

## Operator commands

```text
/stop [run-id]
/cancel [run-id]
/resume [run-id]
/rollback [run-id]
```

Commands are parsed in trusted operator_turn before the active-turn lock, operator limits, approvals, the model or any ordinary message queue. Without an ID they address the session's live/held runs. With an ID they address only that session's matching run. Outside-channel words never invoke these commands. A completed turn is not counted as a successful stop.

| Command | Implemented behavior |
|---|---|
| stop | Persist the flag immediately; withdraw pending approvals; save a control snapshot; refuse later model/tool dispatch |
| cancel | Keep the flag, end the run permanently and close its held requests; preserve all existing effects |
| resume | Refuse while the interrupted turn/tool is still finishing; otherwise lift the flag and reissue withdrawn approvals with new IDs. Old approval answers stay invalid |
| rollback | Stop first, then compensate owned effects newest first: pending replies become discarded and open flags become cleared. Sent/uncertain/unavailable compensation prints none |

A rollback still passes the policy hook as an explicit operator compensation. It cannot touch a foreign run's effect or bypass a policy prohibition. Compensation keys are stable and recorded in the course audit; reissuing a completed compensation does not apply that same key again, even if someone later restored the record. An in-flight call must finish before rollback is attempted; the command stops the run immediately and tells the operator to repeat rollback after completion. Partial compensation is recorded as rollback_partial.

## What is saved

policy/controls.py persists registered session/run identities, status, each dispatched call's tool/arguments/key, in-flight/completed/error state and result. A stop snapshot includes those records and the current trusted request/selected question IDs/route when supplied by the service. After an in-flight call finishes, the registry records its result and updates the snapshot after its tool trace.

This is the Part 2 control/action snapshot. It does not contain the complete planner/model conversation or a Part 1 replay coordinator. Registry's run_id integration parameter must receive Part 1's durable session-plus-run key when multiple tasks share a console session. The first ordinary task retains the legacy session-ID fallback. Replacement and explicitly queued new tasks now receive fresh persisted child IDs from policy/messages.py. Part 1 must use that current ID for checkpoints and waits; cancelled runs are never reused. A new console session also remains available for a fresh task.

Resume fully supports reissuing an interrupted pending approval; that exact saved operation can then execute after a new review. General model/plan continuation is marked awaiting_continuation and is blocked from starting fresh model/tool work until Part 1 takes it over. The command does not replay the original request or reset its budget. Part 1 must load its checkpoint/journal, preserve the shared remaining budget and continue unfinished steps. Its outside-wait callback must use the same run ID and hook; end-to-end outside-wait recovery is still unimplemented in this repository.

## Five stop conditions

| Condition | Evidence | Limit |
|---|---|---|
| Watched | run_live notice before first write; run_resumed notice before newly reviewed work; operator console displays progress | A real operator must actually watch; tests do not establish human attention |
| Fast | Flag precedes later dispatch; an atomic stop-check/dispatch registration closes the hook-to-handler race; model wait checks at <=0.1-second polling intervals | Already-dispatched SDK/tool work cannot be forcibly cancelled |
| Durable | SQLite flag, withdrawn gates and call snapshot survive a new process; completed in-flight writes carry keys/results | Full task checkpoint and automatic remaining-step resume still require Part 1 |
| Safe | In-flight calls finish and are recorded; rollback uses owned effects and reverse order; irreversible sends report none | Partly met: a call already dispatched may still commit after stop; action/record stores are not a distributed transaction |
| Outside agent | Registry and model boundary read the flag; outside input and model text cannot clear it; cancellation cannot be resumed | Enforcement depends on every future role using these shared boundaries |

These qualifications are part of the result: this increment is not a complete durable-execution guarantee.

## Measured free stop checks

[STOP_CHECK.json](evidence/STOP_CHECK.json) retains five observations, source hashes and timestamps. Each test stops an actively blocked free model request, confirms the turn stops without a write, and probes the next registry call to verify refusal. Latency is from the persisted stop flag to that first refused registry probe; it includes waiting for the interrupted turn to return and issuing the probe. It is not an API cancellation benchmark.

- Stops: n=5.
- Median flag-to-refused-probe latency: 0.114 seconds.
- Maximum flag-to-refused-probe latency: 0.117 seconds.
- Model API calls: 0; sandbox writes in these five probes: 0.

Recompute in temporary sandboxes:

```bash
.venv/bin/python -m experiments.analysis.stop_check
# Save a new local evidence snapshot explicitly:
.venv/bin/python -m experiments.analysis.stop_check --output docs/requirements/evidence/STOP_CHECK.json
```

Thirteen control tests cover the five live stops, in-flight committed-write accounting and premature-resume refusal, approval withdrawal/new review, permanent cancel, reverse/idempotent rollback, irreversibility/foreign ownership, outside input, new-process persistence, late stops, hook-to-dispatch race, policy refusal, no guessed replay and per-session multi-run targeting. Latest full suite after disclosed-send integration: 189 tests passed; make check passed all four structural checks. No real-model calls, formal improvement arms, commit or push in this increment.
