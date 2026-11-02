# Assignment 2 report · A plan RepoMind cannot quietly abandon

This report documents the implementation, verification, and measured results of Assignment 2. I completed 72 real Gemini evaluation runs for Part F and 12 real context-retention runs for Part G. Scripted development tests were used to check implementation behavior but were not included in the measured evaluation results.

## Part A · The plan artifact

I used `args_json` to store each tool's arguments as a JSON-encoded string instead of using an object with a union branch for each tool. This keeps the schema relatively small while transferring argument-specific validation to the executor, which parses JSON and checks fixed arguments before executing a tool.

The schema has **0 optional fields** and **0 union types**, below the allowed budgets of 24 and 16. All object fields are required, and objects deny extra properties.

The planner requests `strict: true`, but the Gemini OpenAI-compatible provider did not establish support for strict-schema compilation. Therefore, `strict_compiles` remains `null` in `LAB_02.json`. The automated checker accepted this representation.

## Part B · The validator and the boundary

| Plan | Valid | Failures (step, check) |
|---|---|---|
| `good_export_fix.json` | Yes | None |
| `good_triage.json` | Yes | None |
| `s18_specimen.json` | No | (2, 2), (3, 3), (5, 1) |

`MAX_REPLANS = 2` allows at most three planner requests. If the planner cannot produce a valid plan, the run escalates without executing any tools.

In the measured planned runs, the summarizer recorded **25 schema-error events** alongside 54 initial planner calls and additional revision attempts. These events include plan-validation problems encountered during execution, so they should not be interpreted as 25 failed initial planner requests.

The executor offers only the authorized tool for each approved step. It resolves `$fill` placeholders using the issue and previous execution evidence, preserves fixed arguments, and rejects off-plan tool calls. A comment can be posted only after the required validation and second-pass checks.

In scripted development testing, an unauthorized `post_comment` attempt produced an `off_plan` event and an escalation without executing the comment.

## Part C · Revision at a checkpoint

After the first `search_repo` step, the checkpoint checks whether the search returned at least one `.ts` or `.tsx` source file under `src/`.

A search that returns only documentation or no relevant source-code paths triggers a revision. A revised search is checked again, and `MAX_REVISIONS = 2` limits the number of revisions.

The reviser receives only the plan structure and structured step results, not the issue body. It changes the search strategy while preserving completed steps. Concrete search queries are filled by the executor using the `$fill` placeholder.

The measured checker reported **61 revision events across 54 planned runs**. All accepted revisions were validated and recorded.

Development testing also revealed a limitation: the agent sometimes repeated feature-oriented searches instead of identifying alternative implementation concepts. It safely escalated when its revision budget was exhausted.

## Part D · A second pass before posting

The external verifier uses four checks:

1. **Parse:** The draft begins with valid `label:` and `file:` lines.
2. **Exists:** Any named file exists under `fixtures/repo`.
3. **Seen:** Any named file appeared in the current run's recorded search or read results.
4. **Agreement:** `question` uses `none`, while `bug`, `feature`, and `docs` require a file.

`MAX_ROUNDS = 2` permits a bounded second pass. A draft that continues to fail verification is held, and the run escalates.

| Mode | Detectable checks | Independent evidence | Bounded |
|---|---|---|---|
| Off | No second pass | None | Not applicable |
| Self | Model may identify inconsistencies | No independent source | Yes |
| External | Format, existence, provenance, label agreement | Repository and tool trace | Yes |

Scripted tests confirmed that external verification accepted a previously seen file but rejected unseen and nonexistent file references.

## Part E · Detectors and the diff

For planned runs, the trace diff matches tool calls using the `plan_step` identifier and tool name.

For transcribed traces without `plan_step`, it matches the tool name and all fixed arguments while ignoring `$fill`. Each call can be matched at most once. A step is marked reordered when its matched call appears after a later planned step.

**Looping run**

- Q1 fires on repeated turns (1, 3) and (2, 4).
- Q2 cannot be decided exactly from the plan because it has no `depends_on`; the repeated turns appear to add no new evidence.
- Q3 fires because planned steps 3, 4, 5, and 6 were not completed.
- Q4: The plan addresses the general export problem but does not demonstrate a verified fix before the turn limit.

**Slide 51 (`s49`) run**

- Q1 fires on repeated `search_repo("export")` calls at turns 2 and 4.
- Q2 does not fire in the dependency graph because the relevant steps still feed later steps.
- Q3 fires because step 6, confirming that the button works, was skipped.
- Q4: The agent declared success despite a failing test and without performing final confirmation.

| Planned step | Diff label |
|---|---|
| 1 · reproduce | executed |
| 2 · locate handler | executed |
| 3 · read handler | executed |
| 4 · patch handler | executed |
| 5 · rerun test | executed |
| 6 · confirm button works | skipped |

The repeated `search_repo` call is an extra tool call at trace step 4.

## Part F · What the plan and the second pass bought

I completed 72 real Gemini evaluation runs across four configurations, using six issues with three replicates per issue.

| Configuration | Correct / 18 | Pass rate | Mean tokens | Median latency (s) |
|---|---:|---:|---:|---:|
| Baseline agent | 11 | 61.1% | 12,770 | 4.488 |
| Planned, critique off | 7 | 38.9% | 4,415 | 5.180 |
| Planned, self-critique | 3 | 16.7% | 3,729 | 4.415 |
| Planned, external critique | 6 | 33.3% | 4,408 | 4.366 |

The results show that the baseline agent achieved the highest grounded correctness. The planned configurations consumed fewer tokens but also completed fewer triage tasks correctly.

### 1. What did the plan buy?

Structured planning made the intended sequence of tools observable and enforceable. Each run recorded its initial plan before any tool calls. The validator rejected malformed plans, and checkpoint revisions were bounded.

The checker confirmed that the first plan was recorded before the first tool call in all 66 planned and notes runs. Across the 54 planned evaluation runs, there were 61 recorded revisions.

No off-plan execution events occurred in the measured configurations. However, the earlier scripted tests demonstrated that the boundary rejected an unauthorized action.

Planning without critique achieved 7/18 correct answers compared with the baseline's 11/18. Therefore, the main observed benefit was explicit control and traceability, not improved correctness.

### 2. Where did planning not pay?

Planning and revision consumed a substantial share of prompt tokens:

| Configuration | Mean planning/revision share |
|---|---:|
| Planned, critique off | 54.13% |
| Planned, self-critique | 65.55% |
| Planned, external critique | 52.97% |

For planned runs without critique, the average planning and revision prompt-token cost exceeded the executor prompt-token cost on issues 4202, 4204, and 4206.

For example, on issue 4202, planning and revision averaged 2,276.7 prompt tokens, compared with 1,380.0 for execution. On issue 4204, the corresponding figures were 2,530.0 and 1,343.3.

The per-issue correctness results were:

| Issue | Baseline | Planned off | Self | External |
|---|---:|---:|---:|---:|
| 4201 | 3/3 | 3/3 | 3/3 | 3/3 |
| 4202 | 1/3 | 0/3 | 0/3 | 0/3 |
| 4203 | 3/3 | 3/3 | 0/3 | 2/3 |
| 4204 | 1/3 | 0/3 | 0/3 | 0/3 |
| 4205 | 3/3 | 1/3 | 0/3 | 1/3 |
| 4206 | 0/3 | 0/3 | 0/3 | 0/3 |

The reduction in overall token usage should not be interpreted as greater task efficiency without considering correctness. Some planned runs stopped early because searches or revisions failed to satisfy their requirements.

### 3. What did each second pass buy and cost?

Self-critique achieved 3/18 correct results, lower than the 7/18 obtained without critique. External critique achieved 6/18.

The mean critique-prompt overhead share was approximately 4.74% for self-critique and 1.73% for external critique. These measured shares reflect all runs, including those that escalated before reaching the critique stage.

Self-critique recorded no draft changes. External critique changed one draft and held one draft, but the measured runs contained no successful incorrect-to-correct draft repairs and no correct-to-incorrect changes.

External verification therefore demonstrated an ability to withhold unsupported drafts, but it did not demonstrate an improvement in overall correctness compared with the critique-off configuration.

All configurations scored 0/3 on issue 4206. Neither self-critique nor external critique resolved this difficult case.

### 4. What failed outside the detectors?

The measured results demonstrate that avoiding off-plan actions and repetitive behavior does not guarantee a correct final result.

In the three baseline-agent runs for issue 4206, the expected result was `label: bug` and `file: src/ingest/dedupe.ts`. All three runs terminated with `turn_limit` and did not post a comment.

This is a failure to complete within the execution budget, rather than premature success. No premature-success claim can be established from those three traces.

The Part E `s49` fixture separately demonstrates premature success: the agent declared success after a failing test while skipping the final confirmation step.

Overall, the plan validator and detectors enforce important process constraints, but grounded task correctness still requires checking the actual final output and its evidence.

## Part G · Note-taking against compaction

I completed 12 real Gemini context experiments on issues 4203, 4204, and 4206, with two replicates per issue and progress notes either on or off.

`COMPACT_AT = 350` approximate tokens. The progress file records the task, completed steps, and observed paths, but does not preserve search queries. All 12 experiments underwent compaction before the context questions.

| Configuration | Correct answers | Accuracy | Mean tokens |
|---|---:|---:|---:|
| Notes off | 32/36 | 88.9% | 5,195 |
| Notes on | 33/36 | 91.7% | 5,936 |

The individual results were:

| Issue | Replicate | Notes off | Notes on |
|---|---|---:|---:|
| 4203 | 1 | 5/6 | 6/6 |
| 4203 | 2 | 6/6 | 6/6 |
| 4204 | 1 | 6/6 | 6/6 |
| 4204 | 2 | 6/6 | 3/6 |
| 4206 | 1 | 3/6 | 6/6 |
| 4206 | 2 | 6/6 | 6/6 |
| **Total** | | **32/36** | **33/36** |

### 1. What did the progress file keep and cost?

The notes retained structured task information and exact paths observed during execution, which could be consulted after compaction.

With notes enabled, the agent answered one additional question correctly across 36 questions, improving accuracy by approximately 2.8 percentage points.

Mean token usage increased from 5,195 to 5,936 tokens per run, an increase of approximately 14.3%.

The results were mixed across issues. Notes improved some runs but reduced accuracy on issue 4204's second replicate from 6/6 to 3/6. Consequently, this small experiment does not establish that progress notes consistently improve context retention.

### 2. Which context operations were needed?

**Structured note-taking:** The progress file kept selected durable information, especially completed steps and observed paths. This made important state available outside the immediate conversation.

**Sub-agent isolation:** Separating independent work into smaller contexts can reduce the amount of irrelevant history carried by one agent. However, this experiment did not directly evaluate sub-agent isolation, and a sub-agent summary could omit useful evidence.

**Just-in-time retrieval:** Fetching information when needed avoids keeping every tool result in the active context. The trade-off is an additional retrieval operation and the possibility of failing to recover relevant information.

**Compaction:** Compaction reduced active context size while preserving a shorter representation of prior work. It occurred in all 12 Part G runs, making post-compaction recall measurable.

The longest Part F run by token usage was the baseline agent on issue 4205, replicate 3, using 26,106 tokens. This illustrates the cost of extended agent execution and motivates strategies for managing context growth.

Overall, durable progress notes produced a small recall improvement at additional token cost. The result is suggestive but not strong enough to establish a reliable benefit.

## Assistance

I used OpenAI GPT-6 to help develop reference implementations for the planner, validator, executor, critique mechanisms, progress notes, automated tests, and report generator. I integrated the code into my repository, reviewed the implementation, revised the plan and search instructions during development, and corrected a reporting-completeness condition.

I executed the unit tests, scripted safety tests, Gemini development tests, all 84 official experiments, and the Assignment 2 automated checker. I also inspected traces and used the measured results to verify and interpret the experimental findings before submission.
