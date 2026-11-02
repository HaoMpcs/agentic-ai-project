# Assignment 1 report · Four ways to triage an issue

Every number here also goes in `reports/LAB_01.json`, which the checker reads
(format: `checks/FORMATS.md`, section 7). Give each number its run count. Mark
any vendor figure you cite with its source type and date.

## Part 0 · The recorded trace

Source: one recorded run in `fixtures/week01_recorded_run.jsonl`, computed with
`python -m eval.part0`; model calls are distinct `message.id` values, tool calls
are all `tool_use` blocks, and prompt tokens include input, cache reads and
cache writes once per model call.

| Metric | Value (one recorded run) |
|---|---:|
| Model calls | 21 |
| Tool calls | 23 |
| Cumulative prompt tokens | 399,123 |
| Cache-read tokens | 388,338 |
| Cache-read share | 0.9729782548237009 (97.30%) |
| First prompt tokens | 13,445 |
| Last prompt tokens | 24,188 |
| Cumulative prompt tokens / first prompt tokens | 29.68560803272592 |

As the conversation and tool results accumulate, the prompt grows from 13,445
to 24,188 tokens and repeated reads across 21 model calls total 29.69 times the
first prompt, so caching covers 97.30% of prompt tokens without removing the
growth in cumulative context processed.

## Part A · The loop's bounds

The initial limits in `agent/bounds.yaml` are 12 model calls, 120,000 cumulative
prompt-plus-output tokens, and 180 seconds per run. Twelve calls allow one issue
read, up to eight searches, one comment, one final response and one spare call;
this is a planning allowance, not a fixed tool sequence. The token budget is
30% of the unchanged 400,000-token harness session ceiling. Three minutes allow
about 15 seconds per model call while bounding further work after slow calls.

Pre-run estimates (no real model or evaluation runs):

| Quantity | Initial estimate |
|---|---:|
| F: first prompt tokens | 588 |
| A: additional prompt tokens per step | 1,500 |
| N: maximum model calls | 12 |
| N × F + A × N × (N − 1) / 2 | 106,056 prompt tokens |

F uses the actual system prompt, all three tool definitions and the initial
user-message template with development issue number 4191 (no issue content):
`json.dumps(request, sort_keys=True)` has 2,349 characters, so the four-characters-
per-token estimate gives `ceil(2349 / 4) = 588`. For A, assume one substantial
tool result per step: 20 search hits at roughly 220 characters each (including
path and line number), plus roughly 1,000 characters for the assistant response
and message structure, give about 1,350 tokens, rounded up to 1,500. These are
assumptions, not vendor token counts or measured evaluation results; multiple
tools in a response, long issues, or long outputs can exceed this growth model.
The calculation is `12 * 588 + 1500 * 12 * 11 / 2 = 106056`; it excludes output
tokens, whereas the independent token budget includes them. Measured Part B
values below supersede this estimate in JSON.

<!-- part-b-growth:start -->
Measured across 60 finished Agent runs: F = 519.000000, A = 158.014663, N = 12; N × F + A × N × (N − 1) / 2 = 16656.967742 prompt tokens.

F uses 56 observed first calls; A uses all 341 within-run consecutive-call increases. The 4 zero-call runs have no observed first prompt or call pair. Convention: exclude these missing observations only from F/A, retaining these runs in all run-level metrics. The initial F = 588, A = 1,500 and 106,056-token estimate above is retained for comparison; JSON contains the measured values.
<!-- part-b-growth:end -->

The loop checks turn, token and time bounds in that order before every model
call, preserving assistant content and grouping each step's tool results into
one user turn. It also checks the deadline before each tool call. A call already
in progress cannot be interrupted, so time and token consumption can overshoot
by that call; backend retries count toward elapsed time. Returned tool errors
go back to the model for recovery, while raised tool exceptions are traced as
failed calls and end with `tool_error`. Refusals end with `refusal`; responses
with no tool calls end with `model_stopped`, which does not assert triage success.
Each normal loop exit writes exactly one `end` record; unexpected client errors
propagate to the runner's `crashed` handling.

Validation: `make bounds-smoke` produced two scripted development runs, each
ending with `turn_limit` after 12 model calls and 12 tool calls, with no errors
and trace totals matching client totals. `make test` passed all 15 harness
tests. Additional synthetic checks passed for unchanged assistant content,
grouped tool results, recoverable errors, fatal `tool_error` and `refusal`.
`make check-01` awarded Bounds hold 20/20, covering turn, token and wall-clock
limits plus the reported formula; together with Part 0's 5/5, the automated
total at that checkpoint was 25/80, with no integrity flags. These scripted runs do not measure
triage accuracy or replace the initial F/A estimates; Parts B through D were
incomplete at that checkpoint.

## Part B · Results
The table for all three ways: passes out of 60, per issue out of 10, the spread
(lowest and highest sweep), issues solved in every run, tokens, p50 and p95
latency, cost, tool calls.

<!-- part-b-results:start -->
Computed from finished evaluation traces and tracker comments; crashes remain measured results.
Each way has ten sweeps of six issues. Success requires exactly one correct comment for the run and issue.

| Way | Passes | Sweep min–max / 6 | Issues solved 10/10 |
|---|---:|---:|---:|
| direct | 30/60 | 3–3 | 3 |
| workflow | 22/60 | 2–3 | 2 |
| agent | 26/60 | 0–4 | 0 |

| Issue | Direct / 10 | Workflow / 10 | Agent / 10 |
|---|---:|---:|---:|
| 4201 | 0 | 10 | 8 |
| 4202 | 10 | 0 | 3 |
| 4203 | 10 | 2 | 7 |
| 4204 | 0 | 0 | 0 |
| 4205 | 10 | 10 | 8 |
| 4206 | 0 | 0 | 0 |

| Way (60 runs) | Mean prompt | Mean output | Mean cached | Mean uncached | p50 seconds | p95 seconds | Mean cost USD | Mean tools | Max tools |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| direct | 1244.333 | 48.767 | 0.000 | 1244.333 | 0.834 | 2.280 | 0.00049522 | 2.000 | 2 |
| workflow | 1105.233 | 64.083 | 0.000 | 1105.233 | 1.507 | 103.219 | 0.00049178 | 4.717 | 5 |
| agent | 7388.867 | 172.783 | 0.000 | 7388.867 | 52.865 | 553.074 | 0.00264862 | 5.767 | 12 |

Means include zero-call crashes. Uncached prompt tokens equal prompt tokens minus cache reads.
Costs sum recorded `cost_usd`, treating unpriced calls as zero. Latencies are nearest-rank
percentiles of total elapsed time, including vendor waits. Every tool-call record is counted.

Agent terminal reasons: `{"crashed": 4, "model_stopped": 42, "turn_limit": 5, "wall_clock": 9}`.
Historical unfinished traces excluded and preserved: agent-4201-s08-731567.jsonl.
Lab ledger usage (including development, excluding scripted runs): 1,150,141 / 4,000,000; remaining budget: 2,849,859 tokens.
<!-- part-b-results:end -->

Part B validation: `make test` passed all 15 tests. `make check-01` awarded
60/80 automated points: Part 0 5/5, bounds 20/20, three measured ways 15/20,
grounded checker 5/5, run spread 7.5/10, recomputed numbers 7.5/10, and audit
0/10. All three Part B entries match the checker's independent calculations;
the remaining automated points require Hybrid measurements and the architecture
audit. No integrity flags were reported. The four earlier quota-related crashes
remain measured results; the thirteen newly completed Agent runs recorded no
errors. Parts C and D had not started at the end of that Part B checkpoint.

Development validation history (recorded before evaluation): All runs below used the fixed Gemini 3.5 Flash-Lite configuration,
one job at a time. Success is determined only by exactly one matching comment
for the run and issue; the model's final text and terminal reason do not decide
success. Only development answers were used to grade these attempts.

| Development run ID | Correct | Model calls | Tool calls | Terminal reason |
|---|---|---:|---:|---|
| direct-4191-s01-1aa720 | Yes | 1 | 2 | completed |
| direct-4192-s01-d745f5 | No | 1 | 2 | completed |
| workflow-4191-s01-ab2039 | Yes | 2 | 3 | completed |
| workflow-4192-s01-bf633b | No | 2 | 5 | completed |
| agent-4191-s01-bdf506 | Yes | 9 | 8 | model_stopped |
| agent-4192-s01-c893f1 | Yes | 12 | 12 | turn_limit |
| direct-4191-s02-2a8286 | Yes | 1 | 2 | completed |
| direct-4192-s02-0af837 | No | 1 | 2 | completed |
| workflow-4191-s02-73778b | Yes | 2 | 4 | completed |
| workflow-4192-s02-d3f86e | No | 2 | 5 | completed |

Across these attempts, direct passed 2/4, workflow 2/4 and agent 2/2; these are
development counts spanning prompt revisions, not comparable evaluation
estimates. The agent posted the correct comment on its twelfth call for 4192
before hitting the turn limit. Each architecture has at least one correct dev
run; direct and workflow still miss 4192.

Dev-driven prompt changes before sweep 2: direct initially returned a directory
for 4192, so its prompt now requires a concrete filename and discloses inference
when the summary lacks one. Workflow initially repeated a search with different
capitalization, used a phrase with no matches and invented a filename; its search
prompt now emphasizes distinct terms ignoring case, specific code identifiers
and translating symptoms into code state, while its selection prompt asks for a
complete path from the evidence. Neither revision fixed 4192: direct inferred
the wrong filename, and workflow still returned an unsupported file after weak
search results. No answer paths were inserted into prompts or implementation.
The agent prompt was unchanged. All three classification prompts use identical
label definitions.

Validation: all 15 harness tests passed; synthetic checks covered fixed call
order, tool-free model calls, single formatted posts, and wrong, missing,
duplicate or wrong-issue comments. Every real dev trace matches its client's
token and model-call totals, with no unpriced calls or execution errors.
`make check-01` reports Part 0 5/5, bounds 20/20 and grounded checker 5/5:
30/80 automated, no integrity flags at that development checkpoint. The evaluation
tables above supersede its unfilled results. The architecture audit and Parts C/D
are outside this analysis stage.

## Part C · The decision

### 1. The control-flow diamond

| Component | Who selects the next step? | Who ends execution? | Code |
|---|---|---|---|
| Direct | Code fixes read → one tool-free model call → post. The model chooses comment content, not a tool or branch. | Code returns after posting; the runner records completed or a crash. | `ways/direct.py:20`, `harness/trace.py:79` |
| Workflow | Code fixes read → term generation → one search per term → selection → post. The model supplies terms and label/file; its term count changes the number of searches within this fixed plan. | Code returns after posting; no model-directed repeat or stop decision. | `ways/workflow.py:19`, `ways/workflow.py:39` |
| Agent | The model chooses tools, arguments, order and repetition; the loop executes those choices. | The model can return no tool calls or refuse; code overrides it at turn/token/time bounds or fatal tool failure. The runner handles exceptions. | `agent/loop.py:65`, `agent/loop.py:77`, `agent/loop.py:84` |

Thus model-generated content is present in all three, while the runtime tool-selection diamond is in the Agent. The runner, budget meter and trace writer remain code-controlled components.

### 2. Token multiplier

Agent/Direct = (7,388.866667 + 172.783333) / (1,244.333333 + 48.766667) = **5.847692×**. The calculation uses full-precision JSON values and sums prompt plus output tokens over all 60 finished runs per way.

This exceeds the lecture’s approximately 4× comparison, but does not reproduce that study. First, this experiment uses one fixed Gemini model on six small repository-triage issues, rather than the lecture/vendor workload and model population. Second, the comparison is repeated, bounded episodes against a single tool-free call; all repeated prompt reads, output tokens, quota-crashed zero-call runs and early wall-clock stops remain in the denominator. Third, none of these runs reported cached input, and paid-rate accounting here does not establish the cache or pricing assumptions behind a vendor figure. The lecture figure is the assignment-provided comparator, not a newly verified universal constant.

### 3. Where Agent earns its cost

| Baseline (60 runs) | c: baseline USD/run | m: Agent/baseline cost | Qualifying issues | f | Blended USD/run | All-Agent USD/run |
|---|---:|---:|---|---:|---:|---:|
| workflow | 0.000491778333 | 5.385797 | 4203 | 0.166667 | 0.000851251667 | 0.002648618333 |
| direct | 0.000495216667 | 5.348403 | 4201 | 0.166667 | 0.000854116944 | 0.002648618333 |

The qualifying condition is baseline < 5/10 AND Agent ≥ 5/10, evaluated separately per issue. Only 4203 qualifies against Workflow (2/10 versus 7/10); only 4201 qualifies against Direct (0/10 versus 8/10). In each case f = 1/6. The formula is c × [(1 − f) + f × m], with all-Agent = c × m and all-Workflow = c.

Gate 4 should use Workflow as the assignment’s feasible fixed-process baseline. The Direct version is separately reported for the lecture comparison and remains an important benchmark: Direct actually has the best aggregate result, 30/60, compared with Agent 26/60 and Workflow 22/60. The theoretical blend assumes an oracle routes the qualifying issue share directly to one architecture; it does not pay for a completed Workflow prefix before invoking Agent. It is not a measured Hybrid cost or a deployable routing policy.

### 4. Path entropy

Across all 60 Agent runs there are **13 distinct ordered tool-name sequences**. These are the three most common (ties broken lexicographically):

| Tool sequence | Runs / 60 |
|---|---:|
| (no tools) | 9 |
| read_issue → search_repo → search_repo → search_repo → search_repo → search_repo → search_repo → post_comment | 9 |
| read_issue → search_repo → post_comment | 7 |

Together they cover **0.416667 (41.67%)** of runs. The empty path includes failures/early stops; it is not evidence of an efficient policy. Nine runs follow read → six searches → post. Repeated search counts create distinct paths without necessarily creating useful strategy. Most runs lie outside the top three, so the paths alone do not justify replacing every episode with one fixed sequence; nevertheless, Agent’s 26/60 success at 5.386× Workflow cost does not establish that this freedom earns its price. This is the assignment’s sequence-diversity measure, not Shannon entropy.

### 5. Four gates and preliminary verdict

1. **Task variation — yes.** The six issues produce different evidence needs and labels; Workflow solves 4201/4205 consistently but only 2/10 on 4203, where Agent reaches 7/10.
2. **Bounded damage — partial.** Three tools and turn/token/time ceilings limit action and spending. Repository search excludes config files, but untrusted issue text, private-code access and public comments still create an information-disclosure path; bounds do not enforce confidentiality.
3. **Detection/reversal — partial.** Run-attributed comments and grounded offline checks detect wrong label/file on this known fixture. There is no production oracle, pre-publication review or tool to undo a published comment; later correction cannot undo disclosure.
4. **Economic justification — not established.** Agent adds four passes over Workflow across 60 runs, but costs 5.386× per run and has p95 latency 553.074 s versus 103.219 s. One issue meets the benefit threshold; the value of a corrected triage and a reliable runtime router are not established.

**Preliminary verdict: workflow** among the required agent/workflow/hybrid choices, with human review before production publication. This is a preference for bounded fixed control over unproven general autonomy, not a claim that Workflow beats Direct: Direct is the strongest measured benchmark here. Hybrid is an experiment to test a runtime-visible fallback, not yet the shipping choice. This was the pre-Hybrid conclusion; the final verdict is evaluated in Part D below.

### 6. Predictions — retrospective analysis; original pre-evaluation submission missing

**Provenance.** The required predictions file was not committed and pushed before evaluation, and the original expectations cannot be recovered from the supplied repository history. The new `reports/PREDICTIONS_01.md` is explicitly dated October 8, 2026 and is **not** passed off as a pre-evaluation artifact. It uses only the recorded development results to construct illustrative, smoothed forecasts after the fact: `(dev passes + 1) / (dev attempts + 2) × 60`. The issue-difficulty judgments are also retrospective. Therefore I **cannot truthfully claim to know which predictions I believed before evaluation or which genuine earlier predictions missed**. Instructor guidance is needed on how to grade this late alternative.

| Way | Illustrative estimate / 60 (not preregistered) | Measured / 60 | Difference (actual − estimate) | Illustrative hardest issue | Measured difficulty |
|---|---:|---:|---:|---|---|
| Direct | 30 | **30** | 0 | 4204 | 0/10; tied for lowest with 4201 and 4206 |
| Workflow | 30 | **22** | −8 | 4206 | 0/10; tied with 4202 and 4204 |
| Agent | 45 | **26** | −19 | 4206 | 0/10; tied with 4204 |

**What the preserved traces explain (not invented prior beliefs):**

- **Direct — the aggregate match hides systematic misses.** The illustrative 30/60 estimate happens to equal the measured total, but Direct solves 4202, 4203 and 4205 in all ten attempts while missing the other three in all ten. In `runs/direct-4201-s05-962daf.jsonl`, it selects `src/api/auth.ts` for a password-reset email issue instead of the known `src/notifications/templates.ts`; one call with a summary gives it no search step to challenge a plausible but wrong file. Thus matching the total does not establish that the heuristic predicts which issues are solvable.
- **Workflow — the 8-pass shortfall exposes weak evidence selection.** In `runs/workflow-4202-s06-c89eab.jsonl`, the extractor searches for `TSV`, `CSV` and `XLSX`; `TSV` has no matches, and the resulting fixed-plan selection posts `src/api/reports.ts` instead of `src/exportUtils.ts`. Workflow passed 0/10 for 4202. In `runs/workflow-4203-s03-869f4e.jsonl`, searches for the displayed error match the translation string `src/i18n/en.json`, and the selection posts `src/api/reports.ts` instead of `src/ingest/parser.ts`. Repeated fixed steps do not guarantee useful retrieval or a grounded final file.
- **Agent — the 19-pass shortfall shows that more autonomy is not reliably corrective.** Issue 4206 names `src/export/csv.ts`, but the known answer is `src/ingest/dedupe.ts`. In `runs/agent-4206-s02-afc5b1.jsonl`, the Agent searches and posts the reporter's suggested CSV-writer file, which is wrong; 4206 finishes 0/10 overall. In `runs/agent-4204-s01-2784d4.jsonl`, it reaches the 12-call `turn_limit` without posting a comment; 4204 also finishes 0/10. The Agent does improve on Workflow for 4203 (7/10 versus 2/10), but its extra search freedom and the tiny 2/2 development sample do not justify a forecast of consistently high reliability.

**Lesson and grading limitation.** A two-issue development sample, especially Agent's 2/2, is too small to predict success across six diverse issues, and run failures may also come from provider quotas or termination limits. These concrete traces explain why the illustrative expectations are poorly calibrated; they do not replace the assignment's requested explanation of *actual* missed advance predictions, since none is verifiable. No Git history, original evaluation trace, tracker comment, or recorded measurement was altered to construct this analysis.

### 7. Seven-layer audit

`ARCHITECTURE.md` records all seven layers with implementation references: Model, Tools and Observability are present; Harness, Memory & State, Control & Policy and Evaluation are partial. **EMPTY: 0/7.** Unlike the lecture’s first-build expectation of four empty layers, this assignment already supplies durable tracker/ledger state, metering and traces, and we implemented a grounded evaluator and bounded control. Partial does not mean production-complete: there is no restartable conversation memory, approval/confidentiality policy, history trimming or online quality gate. Prompt-only assurances receive no credit.

## Part D · The hybrid

### Pre-measurement handoff design

**Rule fixed before any Hybrid evaluation:** after the unchanged Workflow has selected a label/file, hand off iff the label is `bug` or `feature` AND either (a) the selected path ends in `.md`, `.rst` or `.txt`, or (b) fewer than two distinct, case-insensitively normalized search queries returned a hit in that selected file. Otherwise publish the Workflow selection. Repeated hits or duplicate queries do not count as independent corroboration.

This is a generic label/file consistency and evidence-support check. It reads only the Workflow selection and search-result paths. It never uses issue IDs, answers, pass/fail labels or hidden fixture data at runtime. Documentation and question classifications stay on the fixed path.

Offline comparison below uses all 60 measured Workflow runs: 38 failures and 22 successes. Known answers are used only by the unchanged grounded grader to score past comments, never as routing features. Search traces contain only 300-character excerpts, so read-only search calls were replayed against the unchanged fixture; every result length and excerpt matched its recorded trace before full paths were used. No run or tracker records were generated or altered.

| Runtime-visible candidate | Fires on failures / 38 | Fires on successes / 22 | Failure precision | Failure recall | False-positive rate |
|---|---:|---:|---:|---:|---:|
| all_searches_empty | 3 | 0 | 100.00% | 7.89% | 0.00% |
| selected_file_absent | 16 | 2 | 88.89% | 42.11% | 9.09% |
| none_for_nonquestion | 0 | 0 | N/A (no triggers) | 0.00% | 0.00% |
| code_label_document | 5 | 0 | 100.00% | 13.16% | 0.00% |
| low_corroboration | 34 | 2 | 94.44% | 89.47% | 9.09% |
| absent_or_document | 21 | 2 | 91.30% | 55.26% | 9.09% |
| selected_rule | 38 | 2 | 95.00% | 100.00% | 9.09% |

The selected combined rule flags 40/60 runs: all 38 observed failures and two successes. It flags ten attempts each on 4202, 4203, 4204 and 4206, and none on 4201/4205. These issue counts are retrospective diagnostics, not runtime branches. The two false positives are the correct 4203 selections, so routing is not a correctness oracle. Performance is measured on the same six issue families used to choose the rule and is therefore optimistic; unseen-issue validation is still needed.

Trace evidence:

- `runs/workflow-4203-s01-75dfea.jsonl`: searches find localization text but the chosen implementation path is absent; handoff fires.
- `runs/workflow-4203-s03-869f4e.jsonl`: the selected API path appears only under one query; low corroboration catches a failure that absence alone misses.
- `runs/workflow-4203-s08-7adb9f.jsonl` and `runs/workflow-4203-s10-8692f1.jsonl`: correct selections are absent from retrieved paths, producing the two false positives.
- `runs/workflow-4202-s01-a6187e.jsonl`: a feature request selects a Markdown document; the document clause catches a failure even when its path appears in multiple searches.
- `runs/workflow-4201-s01-1b91c8.jsonl`: two different searches corroborate the selected implementation path; the correct Workflow result stays on the fixed path.

Expected tradeoff: the rule catches all eight 4203 Workflow failures, where Agent scored 7/10 versus 2/10, but also escalates 4204/4206 where Agent scored 0/10. At this routing frequency it is an expensive experiment, not proof that Hybrid should ship. Applying per-issue standalone Agent pass rates to the routed issues would suggest 30/60 overall; that is a planning estimate, not a measured Hybrid result or a paired causal comparison.

Using all-run mean costs, Workflow-prefix plus 40/60 × standalone Agent estimates **$0.002257523889/run**, before conditioning on routed cases. This exceeds the Part C oracle blend because Hybrid pays for two Workflow model calls on every run, then for Agent on two thirds of runs rather than one sixth. Actual calls, failures, context, costs and routing will be measured afresh.

Fixed control ends at this evidence check. After handoff, the existing Agent selects its own searches, tool order and stopping point under its unchanged bounds; a Hybrid-only tool guard permits at most one post attempt to the original issue. The shared client meter includes the Workflow prefix, while Agent’s step counter and wall-clock deadline start when its loop starts. Workflow is not posted before handoff. Non-handoff runs end `completed`; handoff runs use the Agent loop’s terminal reason. Exceptions propagate to the runner rather than triggering an extra replacement run.

**Measured Hybrid results appear below.** The retrospective routing table above is preserved as pre-measurement evidence.

Hybrid implementation is complete in `ways/hybrid.py`, with pure evidence checks
in `ways/handoff_rules.py`. It reuses `workflow.retrieve`,
`workflow.choose_and_post`, `agent.run`, existing prompts and formatted comment
validation. Seven offline regression checks in `eval/hybrid_checks.py` passed
using temporary fixtures and a scripted response source: fixed-path posting,
handoff ownership, duplicate/wrong-issue post blocking, shared token metering,
provider-error propagation, invalid-selection failure and query normalization.
No synthetic runs were added to the measured dataset.

<!-- part-d-results:start -->
### Measured Hybrid evaluation

Computed from finished evaluation traces and tracker comments; crashes remain measured results.
Each way has ten sweeps of six issues. Success requires exactly one correct comment for the run and issue.

| Way | Passes | Sweep min–max / 6 | Issues solved 10/10 |
|---|---:|---:|---:|
| direct | 30/60 | 3–3 | 3 |
| workflow | 22/60 | 2–3 | 2 |
| agent | 26/60 | 0–4 | 0 |
| hybrid | 31/60 | 2–4 | 2 |

| Issue | Direct / 10 | Workflow / 10 | Agent / 10 | Hybrid / 10 |
|---|---:|---:|---:|---:|
| 4201 | 0 | 10 | 8 | 10 |
| 4202 | 10 | 0 | 3 | 2 |
| 4203 | 10 | 2 | 7 | 9 |
| 4204 | 0 | 0 | 0 | 0 |
| 4205 | 10 | 10 | 8 | 10 |
| 4206 | 0 | 0 | 0 | 0 |

| Way (60 runs) | Mean prompt | Mean output | Mean cached | Mean uncached | p50 seconds | p95 seconds | Mean cost USD | Mean tools | Max tools |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| direct | 1244.333 | 48.767 | 0.000 | 1244.333 | 0.834 | 2.280 | 0.00049522 | 2.000 | 2 |
| workflow | 1105.233 | 64.083 | 0.000 | 1105.233 | 1.507 | 103.219 | 0.00049178 | 4.717 | 5 |
| agent | 7388.867 | 172.783 | 0.000 | 7388.867 | 52.865 | 553.074 | 0.00264862 | 5.767 | 12 |
| hybrid | 8421.483 | 211.933 | 0.000 | 8421.483 | 21.022 | 58.632 | 0.00305628 | 9.700 | 16 |

Means include zero-call crashes. Uncached prompt tokens equal prompt tokens minus cache reads.
Costs sum recorded `cost_usd`, treating unpriced calls as zero. Latencies are nearest-rank
percentiles of total elapsed time, including vendor waits. Every tool-call record is counted.

These are new Hybrid measurements. The preserved 38/38 failures, 2/22 successes,
95% precision and 9.09% false-positive rate above describe retrospective routing
on Part B Workflow traces; they are not measured Hybrid performance.

Hybrid changes success by +9/60 versus Workflow and +5/60 versus Agent. Its cost is 6.214748× Workflow and 1.153914× Agent.

**Handoffs: 38/60**, counted from the six Agent-loop terminal reasons; 21 runs completed in Workflow. 1 further run(s) crashed before handoff, as verified by fewer than two completed model calls and the recorded Workflow traceback. All remain in the 60-run denominator. Ambiguous crashes still stop publication.
Pre-handoff crash traces: hybrid-4204-s09-45137e.

| Issue | Handoffs / 10 | Hybrid passes / 10 |
|---|---:|---:|
| 4201 | 0 | 10 |
| 4202 | 10 | 2 |
| 4203 | 9 | 9 |
| 4204 | 9 | 0 |
| 4205 | 0 | 10 |
| 4206 | 10 | 0 |

Only 4203 met the Part C Workflow-baseline criterion. Those issues received 9 of 38 handoffs. Terminal counts: `{"completed": 21, "crashed": 1, "model_stopped": 31, "turn_limit": 7}`.

Theoretical blended cost: **$0.000851251667/run**; measured Hybrid: **$0.003056278333/run**, 3.590335× theoretical. The measured total decomposes into $0.000488738333/run for completed Workflow-prefix calls and $0.002567540000/run for the Agent suffix, averaged over all 60 runs.

The theoretical formula replaces Workflow with Agent on the qualifying issue share.
Actual Hybrid pays for the Workflow prefix on every run and then pays for the Agent
on the runtime-selected subset. That subset need not match the qualifying share,
and its Agent call lengths/costs need not match the all-issue standalone Agent mean.
The implementation also shares the cumulative token meter across both phases.
These structural differences and the measured decomposition explain why the formula
is not a prediction of the measured sequential Hybrid bill. The final verdict below
is a judgment based on these measurements; this script preserves that judgment.
<!-- part-d-results:end -->

<!-- part-d-verdict:start -->
### Interpretation and final verdict

Hybrid passed 31/60 (51.67%), an observed improvement of 9 passes (15 percentage points) over Workflow and 5 over Agent. It preserves Workflow's 10/10 on 4201 and 4205, reaches 9/10 on 4203 rather than Workflow's 2/10 or Agent's 7/10, and reaches 2/10 on 4202 versus 0/10 and 3/10 respectively. Neither 4204 nor 4206 is solved. These are repeated trials on six fixed issue families, not 60 independent unseen tasks or a randomized causal comparison.

Of 38 handoffs, only 9 (23.68%) went to the Part C qualifying issue, 4203. All nine handed-off attempts passed; its tenth attempt, `hybrid-4203-s09-1f7a94`, stayed in Workflow and failed. Completed Workflow-only runs passed 20/21; Agent handoffs passed 11/38. The remaining no-handoff run crashed. Nineteen handoffs went to 4204/4206, with zero passes, and ten went to 4202 with two passes. The routing rule does find the valuable case but does not concentrate its expenditure there. High retrospective failure-detection precision does not imply Agent can repair those failures.

The preserved `hybrid-4204-s09-45137e` ended with a Gemini 503 while the Workflow's second model call was pending. Its trace has one completed model call and three searches, and its recorded traceback identifies `workflow.choose_and_post`; Agent had not started. It contributes its recorded tokens, cost and full elapsed time to the 60-run metrics, and a failed grade, with no handoff. Together with four earlier quota-crashed Agent runs, it is an observed outcome, not replaced or excluded. The historical unfinished Agent trace has no run_end and remains outside the finished-run denominator.

Hybrid averages 8421.483 prompt and 211.933 output tokens, with no reported cache reads. Its p50 21.022 s is slower than Workflow's 1.507 s and faster than Agent's 52.865 s. Its p95 58.632 s is below both Workflow's 103.219 s and Agent's 553.074 s; those tails include provider waits and come from separate evaluation periods, so they do not prove a structural latency advantage. Its 9.7 mean / 16 maximum tool calls exceed both baselines.

The oracle blend routes one sixth of issues directly to Agent, whereas actual Hybrid first incurs Workflow cost and routes 38/60 (63.33%) onward. The actual prefix is $0.000488738333/run; the Agent suffix is $0.002567540000/run across all runs, or $0.004054010526 per handoff. This selected subset costs more than the all-issue standalone Agent average. The measured $0.003056278333/run is 3.590335× the $0.000851251667 theoretical blend; the higher routing share, paid prefix and longer selected Agent work explain the gap. No retrospective routing precision was substituted for observed Hybrid success.

**Final verdict: workflow.** The preliminary choice remains unchanged among the required workflow/hybrid/agent choices, as a review-assisted baseline rather than an autonomous production publisher. Hybrid's quality gain is real in this sample, but the router sends half its handoffs to two issues neither Agent nor Hybrid solves, costs 6.214748× Workflow and still fails 29/60. Absolute costs are small: Hybrid adds $0.002564500000/run, approximately $0.017097 per additional correct result at the observed rate. Thus cost alone is not a categorical reason to reject it; the unresolved repair effectiveness, safety gates, same-issue selection bias and unspecified business value make general rollout unjustified here. Direct remains an important challenge to this restricted verdict: 30/60 at $0.000495216667/run, only one fewer pass than Hybrid at roughly one sixth the cost. No measured architecture is reliable enough for unattended public triage. Human review is a deployment condition, not an implemented capability or a claim that it was tested.

<!-- part-d-verdict:end -->

## Assistance

I used **OpenAI Codex** to develop and revise the bounded agent loop, Direct/Workflow/Hybrid implementations, prompts, evaluation scripts, result summaries, and portions of this report, including trace analysis and the retrospective prediction exercise. I used **ChatGPT** to edit this assistance disclosure and prepare the citation log. Automated checks of the generated work included `make test` (15/15), seven Hybrid checks, six summarizer checks, and `make check-01` (80/80 automated points). These automated checks do not substitute for my independent review of the AI-generated code and analysis, which remains pending. Prompts, dates, and conversation references are to be documented in `reports/AI_ASSISTANCE_LOG.md` before submission.
