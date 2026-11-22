# Part 2, first implementation: action ranking and policy hook

Owner: Yani Wu. Updated November 22, 2026 (America/New_York).

This increment implements the policy foundation for M2 Part 2 tasks 1–3. It is not the completed approval gate, stop controller or Part 1 recovery. Source: the saved [M2 specification](M2_REQUIREMENTS.txt), Part 2 tasks 1–3, and the current repository implementation.

## Action ranking before gating

Columns use the same class identifiers as policy/autonomy.yaml and policy_decision trace events. First narrow/remove the capability, then examine undo and visibility, then radius, and finally choose the column. A pending internal draft is not a public reply.

| Action class / circumstance | Remove or narrow first | Undo / would someone notice? | Blast radius | Column and reason |
|---|---|---|---|---|
| course_get_question/selected | Only operator-selected question IDs | Repeat read safely; wrong selection visible to TA | One public thread | independent: no external effect |
| course_search_materials/public | Scoped public course index; bounded results | Repeat safely; relevance checked on read | Public source summaries | independent |
| course_read_document/public_active | Public and active sources only | Repeat safely; source identity/version visible | One public document | independent |
| course_read_document/restricted | Remove private/inactive source access | Disclosure cannot reliably be undone | Student privacy or stale authority | prohibited; approval does not restore access |
| course_search_public_answers/public | Public history only; old answer is not authority | Ignore outdated result; current-source validation before draft | Bounded public replies | independent |
| course_create_reply/pending | Persist pending only; no publish capability | Discard exists, visible in course page | One internal draft for one selected thread | independent: reversible and reviewable |
| course_create_reply/staff_only | Remove grade/exception decision authority | Wrong decision may mislead a student even as a draft | One student's grade or exception | prohibited; staff flag instead |
| course_create_reply/private_content | Reject private-record marker content | Later deletion cannot guarantee confidentiality | Private student information | prohibited |
| course_create_reply/invalid_refusal | Only fixed refusal on unauthorized question | Wrong text can disclose or imply access | One thread with privacy request | prohibited |
| course_create_flag/internal | Reason enum only, no copied student text | Clear exists; TA sees flag | One internal staff work item | independent |
| course_status/selected | Only selected question IDs | Repeat safely | One thread's internal effects | independent |
| course_list_flags/operator | Remove tool from model definitions; caller controlled by code | Repeat safely, summary visible to TA | Bounded staff flags | independent for trusted operator |
| course_list_flags/non_operator | No model/student access to operational summary | Staff disclosure not undone by deleting output | Other flagged cases | prohibited |
| operator_limit/approval | Explicit operator rule narrows existing write class | No write occurs before approval | drafts or all writes in this session | requires_approval; saved for per-action approval by policy/approvals.py |
| operator_limit/deny | Explicit operator prohibition narrows existing write class | No write occurs | drafts or all writes in this session | prohibited; overrides an approval rule |
| operator_compensate/owned | Only the run's journalled internal effects; explicit operator command, unavailable to model | Discard/clear, audited; sent messages have no compensation | One owned draft/flag per call | independent for explicit rollback, still subject to policy; no public send |

The remaining manual UI operations are explicit human actions in M1, not autonomous model tools. Their current and planned treatment is recorded to avoid mistaking them for gated agent capabilities:

| Human action / future circumstance | Undo, visibility and radius | Present treatment / M2 follow-up |
|---|---|---|
| Manual draft / staff flag | Discard/clear; visible, one internal record | Human operation; direct sandbox boundary checks remain |
| Discard/restore/clear/reopen | Reverse status transition exists; audit row | Human operation; future rollback controller can reuse compensations |
| Send pending reply as operator | No recall; student sees message in one selected thread | Existing human-reviewed send; not an agent tool or M2 gate |
| Operator-selected automated reply | Irreversible student-visible message in one thread; final body/recipient frozen | Implemented per-action approval; see PART2_DISCLOSURE.md |
| Seed/reset | Resets local demo/run state | Explicit development/runner action, never offered to model |


Automated sending is ranked before gating: narrow to one operator-selected pending automated draft, validate its public sources, then freeze one recipient and the code-disclosed body. Sending has no recall and is student-visible, so `course_send_reply/student_reply` requires approval. `course_send_reply/missing_disclosure` and `/invalid_draft` are prohibited; approval cannot repair them. See [the send contract](PART2_DISCLOSURE.md).

## Enforcement

policy/hook.py loads the operator-owned YAML; the model never receives it. Registry calls execute the following before dispatch and before each bounded transport retry:

1. Read the stop flag for the run. Stop takes precedence over target lookup/classification.
2. Classify using trusted caller/record metadata, not model-provided permission claims.
3. Deny prohibited or unknown action classes.
4. Apply session operator limits; deny wins over approval. Limits never relax a prohibition.
5. Return approval_required without executing the handler if review is required.
6. Execute any additional hook as a further restriction; an exception or any value other than True denies.

The trace records action_class, column, decision, tool, caller, control_run_id and matched limit targets. Normal registry call traces still record the attempted call and its error. Policy implementation errors fail closed. No approval token accepted from a tool argument or student text exists.

## Operator rules now available

From the trusted console, before the active-turn lock or any model request:

```text
/limit drafts approval
/limit drafts deny
/limit writes approval
/limit writes deny
/limit sends approval
/limit sends deny
```

Exact phrases `Do not create drafts until I approve` and `Send nothing until I have read it` are also recognized (case, whitespace and final punctuation normalized). Unknown /limit syntax gets help and is not sent to the model. Other natural-language limits are not silently interpreted: these are the explicitly supported forms.

Rules persist in state_dir()/autonomy.sqlite3 with session, target, mode, trusted source text and timestamp. Outside-channel messages cannot write them. make serve preserves them; sandbox reset removes them. A per-action approval now authorizes only its exact saved call; it does not remove the standing limit. The [gate implementation](PART2_APPROVALS.md) rechecks prohibitions and stop flags. Automated sending now uses an operator-selected, hidden registry capability; sends rules restrict it further and never waive its required approval.

## Interface boundary with Part 1 and later Part 2 work

Part 2 owns policy classes, session restrictions and stop flags. It does not implement a task checkpoint or recovery coordinator in this increment. Registry.control_run_id uses the active harness run ID, falling back to the console session ID; Part 1 integration must pass Registry(..., run_id=its_durable_key) instead of the app fallback before multiple live runs per session are supported.

policy.state.set_stopped(run_id, bool) is now used by the [stop controller](PART2_STOP.md), with console commands, action snapshots, approval withdrawal/reissue and compensation. Full task checkpoint/resume remains a Part 1 integration requirement.

A requires_approval result now halts the workflow/agent and creates a durable request for its exact call; see [approval evidence](PART2_APPROVALS.md). Approval rechecks policy and can execute that one saved operation after restart. General task continuation still requires the shared Part 1 interface.

## Tests

`make test` includes tests/test_autonomy.py (12 policy tests), using temporary sandbox state and no model API calls. It verifies independent draft/no send, same operation blocked by operator approval rule, prohibitions despite an always-yes extra hook, restricted read denied before handler, stop-first ordering and stop-before-retry, policy failures/unknown classes, deny precedence, outside-input isolation, a new-process rule read and reset, commands before session lock, invalid-command rejection and operator-only summaries. These establish the policy foundation, not the complete M2 gate/recovery behavior.

Verification on November 22, 2026: project dependencies installed with make setup; make test passed 114 tests, including the 12 new policy tests; make check passed all four structural checks. No model API requests or measured experiment arms were run.
