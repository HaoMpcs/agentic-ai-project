# Part 2: messages during a task

Owner: Yani Wu. Updated November 22, 2026 (America/New_York). Source: saved M2 Part 2 task 7. Implementation: policy/messages.py, agent/service.py and the shared model boundary; UI help: app/templates/console.html.

## Four explicit dispositions

| Incoming trusted operator message | Disposition | What happens |
|---|---|---|
| /add QUESTION_ID[,QUESTION_ID] | Add to current task | Persist selected question IDs, retain completed work, process additional cases after the current segment without replay |
| /replace QUESTION_ID[,QUESTION_ID] | Replace | Atomically stop the old run and save the new task; retain/list existing effects unless compensation is explicitly selected; start a fresh run after the old turn/tool calls return |
| Ordinary message while busy, or /queue TEXT | Queue | Persist in FIFO order; answer/execute after the task ends, not while a gate/hold is waiting |
| /reject TEXT; invalid/overflow/unknown command | Reject | Tell sender at once; no task mutation, model classification or queued execution |

No model decides whether an instruction adds or replaces. The operator supplies that decision through an exact command. An addition selects known inbox questions, not arbitrary free-form edits to a locked plan. The usual limit remains three questions in the combined task. Trusted metadata selects each added case's workflow/agent route; the model cannot convert a grade/exception question into an authorized public answer.

The inbox is read before every model call, including planner/fill calls through Bounds.model. Observed additions enter those messages as labelled trusted operator IDs and a coordinator-handling notice; raw outside text is not copied into these updates. Fixed workflows also observe updates at their tool boundaries. The live coordinator applies additions after the current segment, skips already-existing live outcomes and reuses the original Bounds object when model work is needed. The task does not receive a new token/step/time budget merely because it was extended.

An atomic end-of-task barrier either claims accepted additions or marks the run complete. A late addition is explicitly rejected rather than accepted and lost behind completion.

## Replacement and earlier effects

```text
/replace SYN-Q-private
/replace --rollback SYN-Q-private
/replace --undo SYN-REPLY-<id>,SYN-FLAG-<id> SYN-Q-private
```

Default replacement retains earlier effects. The immediate acknowledgment lists effects already visible; after the old in-flight call finishes, the final handoff lists the settled effects again. --rollback explicitly selects all owned reversible effects; --undo selects only the listed owned effect IDs. Compensations use the existing policy-checked operator helper, in reverse order. Anything irreversible is reported as none. Unknown/foreign selections are rejected before stopping the original task.

The old stop flag and replacement event are committed in the same control database used for dispatch admission. A later old-run tool cannot be dispatched after that boundary. A tool already admitted may finish; it is recorded, listed and compensated if selected. A late provider worker cannot execute tools. New replacements get a distinct persisted run ID and action-key namespace, so replacing an undone draft for the same question does not return the old discarded effect. Trace events relate parent/original run, replacement message, fresh run and compensation. Model bounds/model calls and registry call traces carry control_run_id to attribute each task separately.

Pending approvals from the old run are withdrawn. New work keeps the session's operator limits and must obtain its own approval. An old approval answer cannot grant permission for the replacement. For scripted runs, the gate also records its root harness run identity so a child action is decided only inside the correct parent run.

## Queue bound and priority

The session admits at most eight non-replacement pending/observed/executing/held message slots. At most one priority replacement can additionally wait. Each foreground drain processes at most nine events; it is not a recursive or unbounded worker. Replacement takes precedence; ordinary queued messages retain FIFO order. Stop/cancel/resume/rollback and supported operator limits bypass the inbox/turn lock. Wrapped commands such as /queue /stop are rejected and must be sent directly.

Queued progress questions are bound to the originating run's recorded question IDs and action keys, even if a replacement has become current before they are answered. They cannot silently report another task's results. Replies are stored and logged with the message/run IDs. If a deferred task raises, the original completed reply is retained, the new task/message becomes held, and no later work automatically runs under that hold. Explicit cancellation closes its queued/held records without undoing earlier effects.

/messages shows persisted message status/answers. Queue displays pending additions, replacements, queued requests and held failures. Completed inbox history is audit data; the eight-slot bound applies to outstanding work, not the size of historical logs.

## Part 1 integration still required

The current live in-process workflow/agent can accept and complete additions. Replacing an approval-waiting task also works because its exact old action can be cancelled without reconstructing a model conversation. Message records and the current run pointer survive a new process; that alone does not resume a crashed task.

An addition made while a durable approval/outside wait is paused stays recorded. General continuation after the answer, an in-flight call left by process death, or an outside reply still requires Part 1's checkpoint/journal/remaining budget and callback. The gate does not guess remaining steps: additions waiting after single-action approval leave awaiting_continuation. After a crash, an executing deferred message is not blindly replayed. Part 1 must restore the correct run ID and inbox cursor and use the same end barrier. These paths remain integration acceptance work, not completed functionality.

## Tests

Seventeen tests in tests/test_messages.py use free models and real second threads. They cover additive work without duplicates; reading IDs before a later model call; replacement before the old write; same-question replacement with fresh keys; selected compensation; FIFO answers; queue capacity and urgent stop; replacement of a pending gate; input/command refusal; outside-input isolation; persisted inbox; old-run progress binding; the combined question limit/end barrier; and a held deferred error preserving the original result.

Two of these tests use tests/support.fixed_run and check_run with tests/fixtures/midtask_add.yaml and midtask_replace.yaml. checks/midtask.py independently reads the completed message operation and actual course effects, applies grounded/no-send checks and rejects a planted old-task write after replacement. These fixtures are driven by concurrent tests, not claimed as serial run.py evidence.

Latest verification: make test passed 173 tests; make check passed all four structural checks with 13 runner task files. No real-model API calls, formal measured improvement arms, commit or push. The earlier stop probes were recomputed after the shared-boundary changes; their method/source hashes remain in evidence/STOP_CHECK.json.
