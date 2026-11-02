# Historical Assignment Evidence for Milestone 1

Owner: Jingyu Huang. The user identified these four ZIP files as their previous homework. Source read date: **2026-11-02 UTC**. This document supplies the Assignment 1-3 references required by M1 Parts 1-3. All prose and newly written analysis code are in English.

## Provenance

| Source | Repository recorded in the archive | Archived HEAD | Use in this project |
|---|---|---|---|
| Assignment 1 | [ylwhale/agentic-ai-assignment1](https://github.com/ylwhale/agentic-ai-assignment1) | `dcda194cb3a0238b2d2a68ad6ab16ae008f45ee6` | Parts 1-3 evidence |
| Assignment 2 | [ylwhale/agentic-ai-assignment2](https://github.com/ylwhale/agentic-ai-assignment2) | `2e9fd0631afd7279ff6f91d569e9324fbbf9f42c` | Parts 1-3 evidence |
| Assignment 3 | [ylwhale/agentic-ai-assignment3](https://github.com/ylwhale/agentic-ai-assignment3) | `84521d35dff1808bb596e08b8724b344f54c25f8` | Parts 1-3 evidence |
| Assignment 4 | [ylwhale/agentic-ai-assignment4](https://github.com/ylwhale/agentic-ai-assignment4) | `74e36f2cd679fe7093642ca47bf79d441d987682` | Reviewed; excluded from M1 implementation |

Repository URLs and HEADs come from archive Git metadata. The retained files are the supplied archive snapshots; no live GitHub verification or claim that every working file matches HEAD is made. The [manifest](../../experiments/assignment_evidence/manifest.json) records each ZIP's SHA-256, original path, source entry and each retained file's SHA-256. No .env, credentials, Git hooks or assignment runtime code were imported or executed.

The evidence bundle retains **216 historical evaluation traces**: 120 from Assignment 1, 72 from Assignment 2 and 24 from Assignment 3. It also retains 24 Assignment 3 call-record files, original reports, answer fixtures, historical price sheets and tracker records/database. All **256 retained source files** are hash-verified before analysis. Assignment 2's 12 notes/compaction runs and Assignment 4's recovery/memory implementation are outside this M1 evidence selection.

These are historical repository-triage experiments, not Course Q&A Assistant runs. They are stored in experiments/assignment_evidence/, never mixed into results/ or linked as this project's formal improvement arms. No model request is made when recomputing them.

## Assignment 1: evidence for the Agent boundary

Source: [LAB_01.md, Part C](../../experiments/assignment_evidence/assignment1/reports/LAB_01.md#L200), [LAB_01.json](../../experiments/assignment_evidence/assignment1/reports/LAB_01.json), the retained runs and [tracker comments](../../experiments/assignment_evidence/assignment1/tracker/comments.jsonl). Model recorded in the traces: gemini-3.5-flash-lite. Each arm has six issues and ten sweeps, or 60 runs.

| Path | Grounded passes | Mean recorded USD/run | Run p50 | Run p95 | Distinct tool-name sequences |
|---|---:|---:|---:|---:|---:|
| Workflow | 22/60 | $0.000491778333 | 1.507 s | 103.219 s | 3 |
| Agent | 26/60 | $0.002648618333 | 52.865 s | 553.074 s | 13 |

The recomputed Agent/Workflow cost multiplier is **m = 5.385797124**. On issue 4203, Workflow passed 2/10 and Agent passed 7/10. Under HW1's criterion (Workflow <5/10 and Agent >=5/10), one of six issue families qualifies, giving f_family=1/6. This is an issue-family criterion, not an observed agent-only share for our course questions and not a production routing fraction r.

For the historical proxy only, Agent adds $0.00215684/run. Dividing by that family share gives $0.01294104; the oracle blend routing 1/6 of families to Agent costs $0.000851251667/run, versus Workflow $0.000491778333 and all-Agent $0.002648618333. The blend assumes perfect routing without a paid Workflow prefix; it is not a measured hybrid or a current-project price.

The long historical Agent p50/p95 motivates visible progress and external limits. These are total run latencies including vendor waits, not M1's per-operator-turn latency. Recorded costs use the archived price sheet, including the source report's treatment of unpriced calls as zero; they are not freshly verified provider prices. HW1 also discloses that its original advance-prediction artifact was missing, so we do not treat it as a preregistered causal finding.

Application: keep predictable lookups and sensitive staff decisions on code-controlled workflows. M1 Part 1 uses Hao Shi's separate Assignment 1 dataset for its primary gate calculation; Jingyu Huang's dataset is supplementary. Neither historical dataset measures current-domain f, c, r or the user's loss v. The present fixtures passing on workflows do not establish incremental Agent value.

## Assignment 2: evidence for plan and critique

Source: [LAB_02.md, Part F](../../experiments/assignment_evidence/assignment2/reports/LAB_02.md#L91), [LAB_02.json](../../experiments/assignment_evidence/assignment2/reports/LAB_02.json), [measured tables](../../experiments/assignment_evidence/assignment2/reports/MEASURED_TABLES_02.md), the retained runs and [tracker comments](../../experiments/assignment_evidence/assignment2/tracker/comments.jsonl). Model recorded in the traces: gemini-3.5-flash-lite. Four arms each have six issues and three sweeps: **18 runs per arm, 72 total**.

| Configuration | Grounded passes | Mean total tokens/run | Run p50 | Runs with exact repeated calls |
|---|---:|---:|---:|---:|
| Agent loop | 11/18 | 12,771.72 | 4.488 s | 3/18 |
| Plan, critique off | 7/18 | 4,415.28 | 5.180 s | 1/18 |
| Plan, self-critique | 3/18 | 3,728.56 | 4.415 s | 0/18 |
| Plan, external critique | 6/18 | 4,407.61 | 4.366 s | 0/18 |

The JSON and raw traces give 12,771.72 mean Agent tokens; this preserves the underlying value rather than the prose report's approximately 12,770. Historical p50 uses nearest-rank total-run latency. M1 Part 4 separately reports median per-turn latency from the project's own records.

### Plan decision

Planning without critique reduced repeated-call runs from 3/18 to 1/18, but grounded passes fell from 11/18 to 7/18. Plan/revision prompts occupied **54.13%** of prompt tokens on average in the planned-off arm. Across all 54 planned runs, 61 revision events and zero off-plan events were recorded. These results support checkable control and traceability, not a general claim of higher correctness or lower cost per correct answer; early stops also reduce token totals.

For M1's batch use case, a plan has consumers: the validator checks coverage and dependencies before effects, and the executor/diff checks what ran. This motivated plan.batch=on in the initial baseline. The project's subsequent Pass 1 passed 0/3 with planning and 3/3 on the bounded loop, so the final setting is plan.batch=off; the plan mechanism remains tested with its switch explicitly enabled. Fixed office-hours lookups need no written plan. HW2's negative quality result is separate evidence, not a verdict that planning improves this project.

### Critique decision

Relative to critique-off's 7/18 passes, self-critique passed 3/18 and external critique 6/18. Mean critique prompt shares were **4.74%** and **1.73%** respectively, including runs that ended before critique. Self-critique changed zero drafts. External critique changed one and held one, with **zero successful incorrect-to-correct repairs**. It did not improve aggregate correctness over critique-off.

Concrete outside-signal evidence: [planned-4206-s01-f0a1b7, line 16](../../experiments/assignment_evidence/assignment2/runs/planned-4206-s01-f0a1b7.jsonl#L16) rejected a file not seen by that run. Line 17 rejected the revised bug/none disagreement; the tracker contains no comment for the run. Holding an unsupported draft is established; fixing the triage is not.

Application: generated course replies use a deterministic source check, actionable feedback and bounded rounds, not self-rereading without new evidence. The critic can verify claims against active public course records without re-solving the task. Fixed refusal wording and categorical flags use direct policy/enum validation. The current tests establish repair/hold mechanics; our real-model experiments must establish utility. Below-line drafts remain pending even when critique passes.

Both required citations can use Jingyu Huang's same Assignment 2 repository; no result from every teammate is required. Reusing results does not mean importing the old implementation. No Assignment 2 execution, notes or compaction code was copied.

## Assignment 3: tool surface and duplicates

Source: [LAB_03.md, Part D](../../experiments/assignment_evidence/assignment3/reports/LAB_03.md#L279), [LAB_03.json](../../experiments/assignment_evidence/assignment3/reports/LAB_03.json), the retained run/call files and [tracker database](../../experiments/assignment_evidence/assignment3/tracker/tracker.db). Model recorded in the traces/report: gemini-3.5-flash-lite.

| Historical tool surface | Starter input tokens | Rewritten input tokens | Difference |
|---|---:|---:|---:|
| Five tools in one request | 386 | 2,536 | +2,150 |
| Planner's textual list | 116 | 1,555 | +1,439 |

These are the homework's reported same-message API measurements. Their raw standalone provider responses are absent from the supplied archive; analysis verifies the reported values' provenance, not a fresh API measurement. Per-run surface-cost scenarios in HW3 are counterfactual calculations based on tool offerings, not observed changes in the API bill. They do not replace this project's separate tool_overhead measurement.

| Historical arm | Runs | Duplicate-comment runs | Max comments/run | Grounded triage passes | Committed write timeouts |
|---|---:|---:|---:|---:|---:|
| Derived keys + readback | 12 | 0 | 1 | 7/12 | 18 |
| UUID keys + no readback | 12 | 4 | 3 | 3/12 | 10 |

The first arm uses sweeps 1/2 and the second 3/4; each contains two runs per issue. Counts are independently recomputed from the archived SQLite environment, not model success messages. Both arms meet the conditional PR rule in 12/12 runs, which is distinct from grounded triage correctness.

The comparison changes key mode and verification together; it does not isolate description length, strict mode or either safeguard individually. It supports stable write identity and confirming reads, not a causal claim that rewritten descriptions alone eliminated duplicates. Current M1 keeps keys and readback; an inconclusive write stops for staff inspection. Full ambiguous-write recovery from the homework is not imported into M1. Historical strict-mode observations do not establish support or limits for the current Google OpenAI-compatible endpoint; M1 Part 3 records the current-provider decision separately.

## Assignment 4 and scope

Assignment 4 contains crash/restart matrices, durable checkpoints and memory/context work. It was inspected to distinguish scope and is recorded in the archive manifest, but none of those implementations or results is used to claim M1 requirements are complete. This avoids adding M2 recovery, persistent task continuation or context work to M1.

## Recompute and remaining work

From a checkout containing the retained evidence:

```bash
.venv/bin/python -m experiments.analysis.assignment_evidence
.venv/bin/python -m unittest tests.test_assignment_evidence -v
```

The offline analyzer validates all source hashes, requires complete unique issue/sweep slots, independently grades tracker effects against answer fixtures, and compares the reused metrics with the archived JSON reports. It makes no network/model requests and does not execute archived scripts. [verified_summary.json](../../experiments/assignment_evidence/verified_summary.json) is its saved output. The three regression tests check reconstruction, rejection of wrong/duplicate effects and detection of tampered evidence.

Verification on November 2, 2026 UTC: all three new evidence tests passed, and
the full project suite passed **101/101 tests**. All four make check checks and
git diff --check passed. Retained logs:
[full tests](../../experiments/reports/assignment-evidence-20261102/make-test.log),
[structural checks](../../experiments/reports/assignment-evidence-20261102/make-check.log),
and [command results](../../experiments/reports/assignment-evidence-20261102/summary.json).

These additions close the missing historical Assignment 1-3 citations. The project now separately contains its model configuration, current tool-definition measurement, baseline and completed Pass 1 with an advance-pushed prediction; see M1 Parts 1, 3 and 4. The 101-test logs above describe the earlier evidence-import checkpoint. Historical homework values are not substituted for the project's own measured results. Final team ownership, disclosure and submission verification remain team responsibilities.

AI assistance: Codex located the archived evidence, wrote the independent offline
analyzer and its tests, and added the English citations. Source hashes, raw
tracker effects and recomputed metrics were checked against the archived reports;
the original evidence files were not edited. The project-wide M1 disclosure
remains the team's responsibility.
