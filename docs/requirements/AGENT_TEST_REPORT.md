# Milestone 1: Agent, Planning and Critique Test Report

Test date: November 1, 2026. Scope follows responsibility 2 selected in this conversation: routing, workflows and the Agent loop, external execution bounds, planner/executor, checkpoints, detectors and execution diff, critique, and related analysis checks. This report does not assign ownership of the product page, sandbox or complete tool model to this role.

## Results and scope

**Mechanism verification passed: 43/43 scoped tests, 98/98 full-suite tests, all four make check structural checks, and git diff --check.** The 43 scoped tests are a subset of the 98 full-suite tests; the counts must not be added. The full suite includes the course starter tests.

This update added eight test methods without changing production Agent code, main tasks, checks, model configuration or switches. Every test that needs a model uses a fake backend marked `free = True` or a free starter scripted backend, through `ScratchTest.run_task` in an isolated temporary folder. The export command copies evidence after each run; the test sandbox remains in its scratch folder.

**These results establish the behavior exercised by the tests. They do not establish real-model accuracy, cost or latency, or completion of the entire milestone.** No real-model baseline, pushed prediction, measured improvement arms or experiment verdict was produced in this verification.

## Version and evidence

- Evidence generated at: `2026-11-01T18:45:05.228105+00:00`.
- HEAD at the time: `66d2e6a2d8b7928049dcf3829d21a841afd173d5`. The tests exercised an uncommitted working tree with `dirty=true`, not a clean clone of a committed revision.
- The recorded source fingerprints remained unchanged during testing. Individual SHA-256 hashes are in the machine report. Rerun verification after changing those sources.
- [Machine report: individual results, source fingerprints and trace line index](../../experiments/reports/agent-tests-20261101/summary.json).
- [Original log for the 43 scoped tests](../../experiments/reports/agent-tests-20261101/unit-tests.log).
- [Original log for the 98 full-suite tests](../../experiments/reports/agent-tests-20261101/make-test.log).
- [Original make check log](../../experiments/reports/agent-tests-20261101/make-check.log).
- [Original git diff --check log](../../experiments/reports/agent-tests-20261101/git-diff-check.log). An empty log indicates success.

The export retains **69 original runner records and their traces**, plus **four direct-call/session traces**, under `results/_free/agent-tests-20261101/`. Runner records and traces were copied without modification. Each record's original `trace` field still names its temporary scratch path; after cleanup, use the copied path listed in the machine report.

All 69 runner records are marked free. Independent task checks passed in 37 records and failed in 32. Those failed task checks are expected observations in negative and fault-injection tests; all 43 test methods passed their assertions. These mixed fault scenarios are not a performance arm, and 37/69 is not a system accuracy estimate.

## Test composition

| Test class or scope | Methods | Result | Coverage |
|---|---:|---|---|
| `tests.test_course.CourseTests` | 18 | All passed | End-to-end tasks, independent checks, external bounds, planning, critique, misrouting, repeated requests, and M1 outside-reply/approval contracts |
| `tests.test_planning.PlanningTests` | 12 | All passed | Executable outcomes, draft revision, completed prefixes, shared revision budget, invalid revisions, generic errors and uncertain writes |
| `tests.test_agent_contracts.AgentContractTests` | 8 | All passed | Routing, planner input isolation, plan validation, placeholder resolution, revisions and feedback contracts added in this update |
| Two detector/executor refusal tests from `RegistryTests` | 2 | All passed | Orphan, repeat, extra and out_of_order detectors; refusal of changed arguments and reordered calls |
| `tests.test_analysis.AnalysisTests` | 3 | All passed | Recomputing records, rejecting fake data as real evidence, and outcome/checkpoint statistics; includes one shared tool-schema statistics test |
| **Total** | **43** | **43 passed; 0 failures, errors or skips** | A method may include multiple subtests or runs |

## Coverage added in this update

| Test method | Purpose |
|---|---|
| `test_each_use_case_reaches_its_declared_path` | Checks actual routing events for all 10 main tasks. Fixed workflows make no model calls, Agent paths do, and effects carry the current run ID. The staff-summary task checks its two preceding workflow routes and its independent summary check. |
| `test_plan_off_batch_still_stops_at_the_external_step_limit` | Explicitly sets control.batch=agent and plan.batch=off. The never-stops backend proves that the loop remains bounded without a plan and that repeats are recorded. |
| `test_initial_and_revised_planner_contexts_exclude_untrusted_text` | Injects a student-text canary into a scratch task. Confirms that the message reached the channel while both initial planner and reviser contexts exclude the text, source bodies and private canaries. |
| `test_revision_cannot_change_an_executed_step_to_another_authorized_id` | Separates authorization from prefix preservation: a revision using an authorized ID must still fail if it changes a completed step. |
| `test_invalid_plan_rules_stop_execution_before_business_writes` | Independently injects an unknown tool, forward dependency, missing outcome, excessive step count, orphan read and duplicate terminal action. Validation stops at its bound before any business write. |
| `test_executed_arguments_resolve_fills_and_match_plan_order` | Checks all 12 actual calls, their step order, resolved arguments, source IDs and draft text. Passing checkpoints do not trigger revisions. |
| `test_critique_repair_feedback_precedes_one_pending_write` | Checks that a repairable error precedes model correction, attempts share the same effect key, persistence happens once, and no message is sent. |
| `test_over_budget_model_response_cannot_dispatch_tools` | A response that exceeds the local token budget cannot dispatch Agent or executor tools, even when it contains tool requests. |

Sources: [new contract tests](../../tests/test_agent_contracts.py), [planning regression tests](../../tests/test_planning.py), and [course scenario tests](../../tests/test_course.py). Assertions use sandbox effects, independent task checks and observable control flow rather than the model's claim of completion.

## Representative trace evidence

Line numbers below refer to the retained original traces. The complete event index is in the machine report. Negative scenarios exercise refusal, stopping and inspection behavior.

| Scenario | Actual run and trace line | Observation |
|---|---|---|
| Batch with planning disabled | [`batch-bound-batch_questions-s01-68ece1`](../../results/_free/agent-tests-20261101/tests.test_agent_contracts.AgentContractTests.test_plan_off_batch_still_stops_at_the_external_step_limit/batch-bound/batch-bound-batch_questions-s01-68ece1.trace.jsonl#L53), line 53 | The never-stops backend reaches the external step limit; no business effect or plan event is produced. |
| Response exceeds the token budget | [`token-dispatch-conceptual_question-s01-e4b82d`](../../results/_free/agent-tests-20261101/tests.test_agent_contracts.AgentContractTests.test_over_budget_model_response_cannot_dispatch_tools/token-dispatch/token-dispatch-conceptual_question-s01-e4b82d.trace.jsonl#L8), line 8 | The run records agent_token_budget; tool requests returned in that response are not executed. |
| Wall-clock limit | [`wall-bound-conceptual_question-s01-4607cb`](../../results/_free/agent-tests-20261101/tests.test_course.CourseTests.test_token_and_wall_bounds/wall-bound/wall-bound-conceptual_question-s01-4607cb.trace.jsonl#L9), line 9 | An accelerated fault injection triggers agent_wall_clock without producing an effect. |
| Repeatedly invalid initial plan | [`bad-plan-batch_questions-s01-fd7929`](../../results/_free/agent-tests-20261101/tests.test_course.CourseTests.test_invalid_plan_replan_bound_and_no_writes/bad-plan/bad-plan-batch_questions-s01-fd7929.trace.jsonl#L13), line 13 | Two validation failures end in plan_rejected; no planned step or business write executes. |
| Planner attempts a tool call | [`off-plan-batch_questions-s01-0b6933`](../../results/_free/agent-tests-20261101/tests.test_course.CourseTests.test_planner_tool_call_refused/off-plan/off-plan-batch_questions-s01-0b6933.trace.jsonl#L8), line 8 | The attempt is logged as off_plan; the planner is allowed only to return a plan. |
| Valid plan and argument resolution | [`contracts-batch_questions-s01-73fbdc`](../../results/_free/agent-tests-20261101/tests.test_agent_contracts.AgentContractTests.test_executed_arguments_resolve_fills_and_match_plan_order/contracts/contracts-batch_questions-s01-73fbdc.trace.jsonl#L55), line 55 | All 12 steps execute in order; actual arguments contain no unresolved $fill; the diff has no skipped, extra or out_of_order entries. |
| Result violates its business postcondition | [`planning-batch_questions-s01-c5e605`](../../results/_free/agent-tests-20261101/tests.test_planning.PlanningTests.test_shape_valid_but_wrong_results_halt_before_next_step/planning/planning-batch_questions-s01-c5e605.trace.jsonl#L11), line 11 | The plan_outcome check fails and execution stops. Other subtests cover an inactive document and an unexpected persisted-effect status. |
| Revision after an empty source search | [`revision-dev_checkpoint_revision-s01-9b892b`](../../results/_free/agent-tests-20261101/tests.test_course.CourseTests.test_revision_only_on_observed_failed_checkpoint/revision/revision-dev_checkpoint_revision-s01-9b892b.trace.jsonl#L16), line 16 | sources_available observes count=0; the revised plan is validated before execution continues. |
| Draft revision | [`planning-batch_questions-s01-b1b878`](../../results/_free/agent-tests-20261101/tests.test_planning.PlanningTests.test_draft_revision_preserves_prefix_and_persists_once/planning/planning-batch_questions-s01-b1b878.trace.jsonl#L23), line 23 | draft_supported triggers version 2; completed steps remain unchanged and each question has one pending effect. |
| Revision changes a completed step | [`contracts-batch_questions-s01-98d925`](../../results/_free/agent-tests-20261101/tests.test_agent_contracts.AgentContractTests.test_revision_cannot_change_an_executed_step_to_another_authorized_id/contracts/contracts-batch_questions-s01-98d925.trace.jsonl#L26), line 26 | The revision is rejected for changing the executed prefix even though the replacement ID is authorized. |
| Shared revision limit | [`shared-budget-dev_checkpoint_revision-s01-213219`](../../results/_free/agent-tests-20261101/tests.test_planning.PlanningTests.test_source_and_draft_checkpoints_share_revision_budget/shared-budget/shared-budget-dev_checkpoint_revision-s01-213219.trace.jsonl#L41), line 41 | Source and draft checkpoints share one revision; exhaustion ends with revision_limit. |
| Invalid revision and skipped steps | [`bad-revision-dev_checkpoint_revision-s01-b743d5`](../../results/_free/agent-tests-20261101/tests.test_course.CourseTests.test_invalid_revision_never_executes_and_labels_skipped/bad-revision/bad-revision-dev_checkpoint_revision-s01-b743d5.trace.jsonl#L23), line 23 | The invalid revision does not execute; the diff identifies the remaining unexecuted steps. |
| Repairable critique feedback | [`critique-feedback-conceptual_question-s01-d24070`](../../results/_free/agent-tests-20261101/tests.test_agent_contracts.AgentContractTests.test_critique_repair_feedback_precedes_one_pending_write/critique-feedback/critique-feedback-conceptual_question-s01-d24070.trace.jsonl#L20), line 20 | Feedback reaches the model before correction; the two attempts share one write key and persist one pending draft. |
| Critique limit | [`nevercorrect-conceptual_question-s01-14a243`](../../results/_free/agent-tests-20261101/tests.test_course.CourseTests.test_critique_correct_revised_and_bound/nevercorrect/nevercorrect-conceptual_question-s01-14a243.trace.jsonl#L32), line 32 | Three rejected drafts end with critique_limit; no draft is persisted and no message is sent. |
| Uncertain write | [`planning-batch_questions-s01-02c3fe`](../../results/_free/agent-tests-20261101/tests.test_planning.PlanningTests.test_uncertain_write_never_revises_or_retries/planning/planning-batch_questions-s01-02c3fe.trace.jsonl#L31), line 31 | ambiguous_tool stops execution without retrying or revising the plan; the existing effect remains available for staff inspection. |

The two direct registry tests also retain `sessions/registry.jsonl`, recording a repeat and two off_plan events respectively. Their paths are in the machine report's `session_traces` list. Orphan detection and synthetic diff outputs are verified by direct test assertions, not represented as real-model runs.

## Bounds and failure semantics

Current default external bounds are 24 combined model/tool steps, 32,000 accounted tokens and a 45-second wall clock. A batch plan permits at most 16 steps. Initial planning permits one re-plan, and each run permits one checkpoint revision. Critique checks at most three drafts. Both checkpoints share the revision budget, so a planned run can end at revision_limit before reaching three critique attempts.

The never-stops test uses the default step limit. The token test uses synthetic fake usage. The wall-clock test temporarily shortens the limit to 0.03 seconds and simulates a slow response. These tests exercise the limit mechanisms; they do not run a real provider for 45 seconds or measure real token costs.

An invalid initial plan produces no business write. A failed postcondition stops subsequent execution. If an effect has already been persisted when a postcondition fails, the test requires retaining it for inspection rather than claiming a rollback. An uncertain write stops for staff inspection without adding M2 recovery behavior. Drafts remain pending; publication requires the operator's manual product-page action.

Tasks often include a follow-up question, so the final end_reasons entry can be follow_up. To diagnose the main task, read the entire end_reasons sequence and trace rather than only end_reason.

## Reproduction

From the repository root, with dependencies installed, run the main scoped test classes:

```bash
.venv/bin/python -m unittest \
  tests.test_course.CourseTests \
  tests.test_planning.PlanningTests \
  tests.test_agent_contracts.AgentContractTests -v
```

To regenerate the machine report with all 43 scoped tests, the full regression suite, structural checks and original evidence:

```bash
.venv/bin/python -m experiments.analysis.agent_test_report
```

The command creates a fresh directory with a UTC timestamp and prints its summary.json path. Use `--output experiments/reports/<new-directory-name>` to choose a new directory. It refuses to overwrite an existing output directory or its corresponding free-evidence directory. Model tests still execute inside ScratchTest folders.

## Historical real-evaluation handoff

This verification did not read or print API keys, choose a model, make paid API calls, or run git commit, push or an m1 tag operation. At this verification checkpoint the provider/model fields were unconfigured. Subsequent team commits configured the model and completed the real baseline and Pass 1; see M1 Part 4 and experiments/LEDGER.md. The checklist below records the original handoff. Items 1–5 were subsequently addressed by the retained baseline, Pass 1, M1 Parts 1–4 and assignment source review; they are not current experiment tasks.

1. The team must select the model, price and runtime configuration, complete the four-gate justification for Agent routing, and freeze the tasks and checks. Routing tests prove that configured paths are followed; they do not prove that an Agent is preferable to a workflow. The earlier diagnostic in which every main task passed on workflows still needs to be addressed.
2. Commit engineering corrections as part of the baseline, then run every main task for three sweeps and inspect all records and traces. Responsibility 2 owns diagnosis of Agent, plan and critique behavior in coordination with the evaluation owner.
3. Choose an improvement from an observed real problem. Fill the ledger with the problem, evidence, numeric prediction, switch and owner. Commit and push the prediction before running two new measured arms.
4. Complete the chosen pass's required analysis with the evaluation owner, such as runs with repeated calls and false finishes determined from completion status plus the independent task check. Existing event totals do not establish those metrics by themselves.
5. Record the verdict, decision table and final switch settings. Actual Assignment 1-3 figures and references were subsequently added to M1 through the [assignment source review](ASSIGNMENT_EVIDENCE.md); those historical figures do not replace the project's own experiments. Passing these mechanism tests does not replace the remaining requirements.

The new tests are ordinary verification work. Required outcome checks, detectors and diff were not disabled to manufacture a comparison, and free records were not linked as a formal pass. Final clean-clone verification and submission tagging remain to be performed once the code and materials are complete.

AI assistance: Codex wrote the added contract tests, evidence-export command and this report. Results were checked by running tests, inspecting sandbox effects, retaining original traces and verifying logs. The team must still complete the project-wide AI assistance disclosure in M1.md.
