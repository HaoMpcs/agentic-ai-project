# Part 2: persisted per-action and fixed-plan approval gates

Owner: Yani Wu. Updated November 22, 2026 (America/New_York). Source: user-supplied M2 Part 2 task 4 and the local implementation. This increment follows [the policy foundation](PART2_POLICY.md).

## What is implemented

policy/approvals.py stores pending requests in state_dir()/autonomy.sqlite3. A request contains the originating session/run ID, tool, immutable arguments, original action key, caller, authorized/read IDs, trusted-record digest, computed screen, operator restrictions and runtime switch snapshot. Repeated identical pending calls share one review. These are gate records, not Part 1 task checkpoints.

`approval.reviewed_send=plan` is the plan-level case. `/send` has already fixed
the selected draft, recipient thread, final disclosed body, source IDs and action
key, so its screen lists the exact read/check prefix and gated send before any
step executes. Approval authorizes only those resolved calls. Policy, sources,
disclosure and exact outgoing arguments are checked again; a revised or unlisted
send creates a new review. `per_action` remains implemented as the comparison
setting. Generated replies remain per-action when an operator limit gates them,
because their content is not fixed by an eligible upfront plan.

When the policy hook requires approval, the registry creates a request without executing the write. The service ends the turn and directs the operator to Approvals. Ordinary task messages in that session are held while a request is pending/executing/uncertain. Limit commands still take effect before the session lock. The queue page already lists pending approvals through the shared service; sandbox/queue.py additionally lists executing/uncertain/blocked/failed approval outcomes for inspection.

The approvals page shows the exact internal draft/flag and code-computed scope/checks, then the student's original words labelled untrusted. It accepts approve or deny through harness.turns.decide_approval and agent.service.decide_approval, the same path used by scripted task approvals. HTML escaping prevents student text from becoming executable markup.

A denial creates no effect. An approval atomically claims only a pending request, rechecks the stop, current policy/limits, question/student input/source snapshots and runtime settings, then executes exactly the stored call through the registry. It restores the server-recorded read/selection context, preserves the saved key and checks the result. Knowing a pending approval ID is not permission; only an executing operator-approved matching request authorizes the operation. Prohibition, stop and additional hook failures still deny.

Repeated approve clicks cannot repeat an operation; a rejected request cannot later be approved. A process crash after a decision was claimed leaves executing visible in the queue; this increment never guesses whether that call committed or blindly repeats it. Ambiguous/internal/transport outcomes stay uncertain for inspection.

## How to try it

```bash
make app BACKEND=tests.fakes:GoodAgent
```

In one console session:

```text
/limit drafts approval
Process SYN-Q-deadline
```

Open /approvals. Before a decision, there is no draft effect. Approve to create the exact pending draft or deny to leave the sandbox unchanged. The draft stays internal; it is not sent to the student. make serve preserves the request; a new process can approve it without calling the model again.

Development task: tasks/dev/approval_draft.yaml. Its scripted yes uses the same callbacks. checks/approval.py independently compares the approved arguments/key to the actual course effect and applies the existing grounded/no-send check.

## Screen inventory

The currently gated class is operator_limit/approval for an explicitly restricted internal draft or staff flag. These are not yet external-send approvals.

| Screen item | Origin | What the operator can verify |
|---|---|---|
| Tool and exact argument body/reason/source IDs | Computed serialization of the saved call | The precise change being approved |
| Resulting pending/open status; publishes_to_student=false | Computed from current tool semantics | This creates an internal record only |
| Question ID, stored kind/topic and existing-record origin | Computed from sandbox records | The target question and its scope |
| One changed record and zero external recipients | Computed from current single-effect tool | Blast radius |
| Sources active/public and private-marker check | Computed from referenced records/body | Source eligibility and a narrow privacy check, not a guarantee of all privacy properties |
| Source-check verdict/detail | Deterministic extractive validator | Whether current public facts support the proposed draft; approval does not bypass validation |
| Student author/text | Original outside-channel text, explicitly untrusted | The question being answered, not an operator instruction |
| Session/run/time | Stored control metadata | Where the answer returns and how long review waited |

No model rationale is presented as a computed fact. Every approval_decision trace records the action class, original screen, decision, actual actor (operator vs scripted_operator), elapsed wall seconds, mode, switches, run ID and key. Scripted elapsed times are not evidence of human reading time.

## Part 1 boundary and remaining Part 2 work

A request survives restart and can execute its one saved operation. Resuming all remaining model/workflow/plan steps, with their journal and shared remaining budget, still belongs to the Part 1 integration. This gate does not re-run the original task to guess continuation. Registry(..., run_id=durable_key) is the integration point for an app session with multiple runs. The inbox now persists fresh child IDs for replacement/queued tasks; Part 1 must reuse those IDs and the gate records the root harness ID for scripted child decisions. After a reviewed call completes, Part 1 should record its result and continue any remaining steps from saved state.

[Unknown-write holds](PART2_ESCALATION.md) settle confirmed committed actions
without replay. [Stop controls](PART2_STOP.md) withdraw pending requests and
reissue them under new IDs on resume. Fixed-plan reviewed-send approval,
re-gating of unlisted actions, external sends and disclosure are implemented;
[live mid-task add/replace/queue handling](PART2_MESSAGES.md) is also implemented.
A5 attribution, real-human review measurements and final framework analysis
remain report work.

## Verification

November 22, 2026: tests/test_approvals.py passed 15 tests. They cover unchanged sandbox before decision, exact saved call/key, denial and duplicate decisions, approval in a new process, stale sources/question rejection, later stop/prohibition, outside text not granting approval, escaped actual HTTP screen, concurrent decisions, unclaimed ID/argument tampering, interrupted execution held, fail-closed policy revalidation, request deduplication and the scripted task's independent check. make test passed 129 tests; make check passed all four checks with 13 task files. No model API requests, measured passes or real-human timing study were run.
