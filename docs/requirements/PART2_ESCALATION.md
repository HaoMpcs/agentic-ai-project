# Part 2: unknown-write escalation and durable hold

Owner: Yani Wu. Updated November 22, 2026 (America/New_York). Source: saved M2 Part 2 task 5, implemented in policy/escalations.py and integrated with the registry, service, planner and queue.

## Signal, packet, hold and budget

The named signal is write_outcome_unknown. It applies to draft/flag writes whose dispatch returns an ambiguous timeout, an internal failure or exhausted transport failures, since those outcomes do not establish that the effect is absent. It does not apply to a read timeout or an invalid search argument. No model confidence score triggers it. Normal confirmed writes and ordinary public lookups do not create a hold.

Each hold saves the original session/run, exact tool/arguments/key, read/selection context, call/plan identifiers, any approval ID and current settings in the control store. This is an action-level recovery packet; it is not Part 1's full task checkpoint/journal. The three nonempty human fields state what was attempted, why it stopped and what the TA needs to inspect. The registry persists the hold before returning the failed call; subsequent registry calls for that run are refused. Workflows, agent loops and planned execution return with escalated_held, without revising the failed write or dispatching later calls.

policy/autonomy.yaml sets an initial daily review cap of 20 and a hold deadline of 86,400 seconds (24 hours), with calendar days evaluated in America/New_York. These are design defaults, not a measured reviewer capacity. The cap counts all approval requests created that day plus already-notified escalations. In a SQLite immediate transaction, a new escalation reserves its notification only if that count is below the cap. Repeated identical holds do not spend another slot. Resolved requests still count on their creation day.

Past the cap, the run still holds and the queue marks over_cap, but no three-field escalation packet is pushed into the console trace/reply. The operator can deliberately open it with /escalations. Silence never approves or retries anything. A past deadline adds timed_out to inspection/queue output and leaves the run held; there is no background worker that executes on timeout. Stop takes precedence over held-run inspection completion.

## Operator handling

In the trusted console, including a new session after make serve:

```text
/escalations
/resolve <escalation-id> confirm
```

The first command explicitly opens active hold packets. The second does not trust the word confirm: it independently reads the environment by the original action key and compares the question, operation kind and exact body/sources or flag reason.

| Environment read | Action |
|---|---|
| Identical committed effect found | Resolve hold using the existing effect; no tool/write replay. An uncertain approval for that same action is also marked executed |
| No effect found | Mark awaiting_recovery; remain blocked and expose the saved call for Part 1's same-key recovery |
| Read unavailable or different content under key | Stay held for TA investigation; no default execution |
| Run stopped | Stay held; confirmation cannot lift the stop |

Every answer logs operator session, original run, outcome and repeated_call=false. Outside messages cannot call this handler. A new process and a different trusted operator session can settle a confirmed existing effect. It does not automatically resume remaining model/plan steps; Part 1 must use its checkpoint and journal for that continuation. No irreversible external send has been added in this increment.

## Queue and integration boundary

The queue lists hold ID, status, original session/run, deadline, timed_out and over_cap. The policy hook checks active escalation holds before any later dispatch. The existing approvals page remains for decisions; an escalation is a separate run-time signal and packet.

Part 1 integration must provide its durable session-plus-run ID to Registry, record these saved calls in its task checkpoint and complete the absent-effect same-key retry and remaining-step resume. It must not rerun the model to invent new arguments. This increment deliberately leaves awaiting_recovery blocked until that integration exists. The milestone's full checkpoint/absent-retry/resume acceptance criterion is therefore still incomplete.

## Tests and scope

Fourteen tests in tests/test_escalations.py cover pre-commit failure with no write, after-commit uncertainty with one effect, no dispatch after hold, silent/expired hold, later-session/new-process confirmation with no duplicate, absent-effect handoff, unavailable/mismatched readback, cap suppression, approvals sharing the cap, outside-input isolation, HTTP queue/console visibility, stop precedence/reset, read-error exclusion, workflow packet delivery and settling an uncertain approved write. The planning regression now expects escalated_held and verifies the persisted signal while retaining its one-write/no-revision assertions.

Verification: make test passed 143 tests; make check passed all four structural checks with 13 task files. These are free tests in temporary sandboxes, not measured M2 improvement arms. No model API request, real-human attention study, Part 1 execution implementation, commit or push was performed.

Stop controls are now implemented in [PART2_STOP.md](PART2_STOP.md). Stop prevents confirmation; resume lifts only the stop and does not silently settle an escalation. Cancel closes the held request while preserving effects, and explicit rollback compensates only owned reversible effects.
