# Assignment 3 · A tool surface that tells the truth, and writes that happen once

## Part A · The five definitions

- Audit: **5 strict tools, 0 optional parameters, 0 union/nullable parameters**.
- My vendor (OpenAI, `gpt-4.1-mini`) has strict mode. `make ping` sent all five
  definitions with `strict: true` in one request and it was accepted (served by
  `gpt-4.1-mini-2025-04-14`; the record is in `runs/_ping.jsonl`).
- Consolidation: I found no chain worth merging. How many searches and reads a run
  needs depends on what it finds, and the two writes need separate outcomes, so
  the five roles stay separate.
- Naming: I prefixed every tool with its service: `tracker_read_issue`,
  `tracker_post_comment`, `code_search`, `code_read_file`, `pulls_open_pr`. The
  file names are unchanged.

Each parameter description says what changes when it is set, what it costs and
when to pick it. I used made-up issues 4417/4418 in the examples so they would not
hint at the dev answers. The first example is the typical call and the second is a
case the schema leaves unclear. The registry renders the examples into the end of
the description and sends the vendor only name, description, input_schema and
strict. Search filters by `path_glob`, a validated glob, instead of a free-text
filter. Reads and write acknowledgements return IDs like `issue-4417`.

The result shapes live in the tool modules. Search returns JSON
count/query/query_valid/truncated/index_age even for zero hits, while blank,
overlong or malformed queries/globs are errors. Search retains starter literal
content matching and path/line ordering; deep means current disk, not expanded
archive access. Concise/detailed cap excerpts at 160/500 characters and file text
at 4000/20000. The issue text cap is 12000. Write acknowledgements are limited to
1000 serialized characters. All responses carry cap and truncation metadata.

Before dispatch, the registry checks required and extra fields and types,
lowercases enum values without touching other strings, and applies the length and
range rules in `tools/boundary.py` (kept out of the vendor schemas). After the tool
runs, it checks the result against the shape I declared for it, including size,
counts and whether `truncated` is consistent, before the model sees it. If the
planner leaves a `$fill` placeholder in an argument, the executor fills the whole
argument; anything still unresolved is rejected at the boundary. File lookup
requires an exact-case match, so macOS's case-insensitive disk cannot open the
wrong file.

### search_repo before and after

All fields of both definitions; "Absent" means the starter did not have the field.

| Definition field | Starter (before) | Current (after) |
|---|---|---|
| `name` | <code>&quot;search_repo&quot;</code> | <code>&quot;code_search&quot;</code> |
| `description` | <code>&quot;Search the code.&quot;</code> | <code>&quot;Find candidate repository files by literal, case-insensitive substring matching of line contents, not filenames; do not use regex, SQL or a query language. Searches text outside config/, node_modules/ and .git/. Use one short identifier or phrase, not an entire issue sentence. query must contain non-whitespace and be at most 200 characters. path_glob is an explicit relative glob selector, not a free-text filter expression. Returns JSON results [{path,line,text}], count (displayed hits), total_count (all matching lines), query, query_valid, truncated, index_age, cap_results, cap_excerpt_chars. Results stay in path/line order. Empty results with count=0 and query_valid=true mean a valid search found nothing; blank/overlong queries and malformed globs are execution errors. Default max_results=10, allowed 1..20. response_format concise is the cheap default, with 160 characters per excerpt; detailed permits 500. truncated signals omitted hits or shortened excerpts. index_age gives the prebuilt index age, or live disk when deep=true. Serialized response cap is 32000 characters.&quot;</code> |
| `input_schema` | <code>{&quot;type&quot;: &quot;object&quot;, &quot;properties&quot;: {&quot;query&quot;: {&quot;type&quot;: &quot;string&quot;, &quot;description&quot;: &quot;Text to look for&quot;}, &quot;max_results&quot;: {&quot;type&quot;: &quot;integer&quot;, &quot;description&quot;: &quot;How many results. Default 10.&quot;}, &quot;filter&quot;: {&quot;type&quot;: &quot;string&quot;, &quot;description&quot;: &quot;Optional filter expression&quot;}, &quot;deep&quot;: {&quot;type&quot;: &quot;boolean&quot;, &quot;description&quot;: &quot;Whether to do a deep search. Default false.&quot;}}, &quot;required&quot;: [&quot;query&quot;]}</code> | <code>{&quot;type&quot;: &quot;object&quot;, &quot;properties&quot;: {&quot;query&quot;: {&quot;type&quot;: &quot;string&quot;, &quot;description&quot;: &quot;A literal symbol or short phrase of 1..200 characters including non-whitespace. Changing it changes matched lines; narrower terms reduce result context. Search with a second term if the first finds nothing.&quot;}, &quot;max_results&quot;: {&quot;type&quot;: &quot;integer&quot;, &quot;description&quot;: &quot;Maximum displayed matching lines, 1..20; choose 10 normally. Higher values expose more evidence but consume more context; total_count still reports all matches.&quot;}, &quot;path_glob&quot;: {&quot;type&quot;: &quot;string&quot;, &quot;description&quot;: &quot;Relative file selector, 1..500 characters. Use * for the whole searchable repository; choose a narrower glob only after evidence suggests a location. Supports *, ?, paired [], and {a,b}; e.g. src/**/*.{ts,tsx}. No &#124;, commas outside braces, spaces, absolute paths or .. traversal.&quot;}, &quot;deep&quot;: {&quot;type&quot;: &quot;boolean&quot;, &quot;description&quot;: &quot;False normally searches the cheap prebuilt index. True reads current disk files, increasing local I/O; choose it when index freshness matters. It does not change literal matching or include excluded directories.&quot;}, &quot;response_format&quot;: {&quot;type&quot;: &quot;string&quot;, &quot;description&quot;: &quot;Choose concise normally to minimize returned context; detailed increases the text cap for close inspection. This changes output size, not which file or query is selected.&quot;, &quot;enum&quot;: [&quot;concise&quot;, &quot;detailed&quot;]}}, &quot;required&quot;: [&quot;query&quot;, &quot;max_results&quot;, &quot;path_glob&quot;, &quot;deep&quot;, &quot;response_format&quot;], &quot;additionalProperties&quot;: false}</code> |
| `strict` | Absent | <code>true</code> |
| `examples` | Absent | <code>[{&quot;input&quot;: {&quot;query&quot;: &quot;parseAmount&quot;, &quot;max_results&quot;: 10, &quot;path_glob&quot;: &quot;*&quot;, &quot;deep&quot;: false, &quot;response_format&quot;: &quot;concise&quot;}, &quot;note&quot;: &quot;Typical: search the entire indexed repository for a single identifier.&quot;}, {&quot;input&quot;: {&quot;query&quot;: &quot;invalid currency&quot;, &quot;max_results&quot;: 20, &quot;path_glob&quot;: &quot;src/**/*.{ts,tsx}&quot;, &quot;deep&quot;: true, &quot;response_format&quot;: &quot;detailed&quot;}, &quot;note&quot;: &quot;Hard: a multi-word literal phrase and brace alternatives are valid; &#124; alternatives are not. Live disk avoids stale index content; detailed spends more context.&quot;}]</code> |

### Verification and development evidence

1. Baseline `make test` passed all 60 tests and a real starter `make ping` passed.
2. Rewritten JSON and roles passed `make audit`: 5 strict, 0 optional, 0 union.
3. The real ping accepted the five new strict tools, including rendered examples.
4. After boundary implementation, `make test` passed 58 tests and skipped the
   two starter-behavior tests. `python -m unittest eval.test_tools_03` passed 11
   contract tests covering all required fields, type errors, unknown fields,
   execution-before-validation prevention, content rules, malformed/empty search,
   case handling, truncation, malformed outputs and vendor-field filtering.
5. One live dev invocation ran both issues, costing 23024 tokens and approximately
   $0.0114. Traces: `runs/planned-4191-s01-509776.jsonl` and
   `runs/planned-4192-s01-dc92a0.jsonl`. Both ended completed, all tool calls used
   the new names, and none returned a tool error. Tracker comments were
   `label: docs / file: README.md` and
   `label: bug / file: src/components/ExportButton.tsx` respectively.

The 4191 run searched for the command in the issue and read README.md before
posting. The 4192 run used up its searches, read a documentation file, and then
named a source file it had never read. The label and path look right, but they are
not grounded in anything the run read, so I count this as a limitation of the dev
result. Critique was off, and these runs came before Part C's draft-before-write
changes.

## Part B · Errors

### Failure classification (Task 1)

| Tool role | Transient | Permanent | Ambiguous |
|---|---|---|---|
| read_issue | Temporary read timeout/connection interruption or retryable local I/O | Invalid/missing issue; inaccessible, missing or malformed fixture | None with a durable side effect: it is read-only, so a lost read response can be retried |
| search | Temporary index/disk read interruption or retryable local I/O | Invalid query/glob/limit/format; missing/corrupt index or access failure. A valid zero-hit result is success | None with a durable side effect: it is read-only |
| read_file | Temporary read timeout/connection interruption or retryable local I/O | Missing/wrong-case/binary/excluded/outside path; denied access or a file disappearing during read | None with a durable side effect: it is read-only |
| comment | Only transport failure explicitly known to occur before dispatch | Invalid/missing issue or invalid body; permission/resource failure | Dispatched write timeout or connection drop: comment may already exist |
| open_pr | Only transport failure explicitly known to occur before dispatch | Invalid/missing issue, wrong branch, invalid title/body; permission/resource failure | Dispatched write timeout or connection drop: PR may already exist |

The read tools only touch local fixtures, the index and the disk, so they never
hit a real rate limit; I injected the transport failures in local tests. An
adapter reports a transient failure by raising `TransientTransportError` with
`retry_after`, and a write counts as transient only if it also says
`before_dispatch=True`, because a bare connection error on a write does not prove
the request never left. The reads have no ambiguous class: they can time out, but
there is no side effect to reconcile. The per-role lists are in LAB_03.json.

### Error routing (Task 2)

Protocol policy: **end_run**. An unknown tool name or non-object arguments are
written in full to `runs/<run_id>.harness.log` and raise a generic
`ProtocolError`. Both the agent loop and the planned executor then end the run
with `tool_error` before sending another model request, so no unanswered tool call
is left and the model never sees the protocol details. I chose to stop because
rewording the arguments cannot fix a tool that does not exist; a generic result
would only let the model waste turns trying.

Ordinary execution failures return `is_error: true`. A bug in my own code, or a
result with the wrong shape, is logged privately and ends the run with a generic
system error, since the model cannot repair application code. Part A's
malformed-result test covers this.

### Repair facts (Task 3)

The repair fact comes first and the details after it. Messages are capped at 1200
characters, with room kept for the retry advice, and the field name and valid enum
values survive even when the bad input is very long. A missing issue lists the
issue numbers that do exist. A permission error says access must be restored and
that repeating the call will not help. Binary, path, glob and value errors name the
fix. OS and implementation details never reach the model.

`code_read_file` checks the path against the repository's file list with exact
case. Near matches come from files in the same directory with a similar stem, plus
spelling similarity; no fixture path is hard-coded. The actual error for
`src/report.ts`:

```text
Error: path: Choose an exact case-sensitive path: src/Report.ts, src/report.tsx, src/reports.ts. No such file: src/report.ts. Change the named argument before retrying; repeating unchanged input will not help.
```

### Retry allocation (Task 4)

`tools/errors.py:invoke` makes at most **3 transport attempts** per read call;
write retries are handled separately in Part C. It waits 0.1 s, then 0.2 s, or
longer if the adapter's `retry_after` asks for it, up to 5 s. If the service asks
for a longer wait, the loop stops and reports that to the caller instead of
retrying early. Validation runs first, and semantic failures and bugs are never
retried. Every retry reuses the same normalized arguments, with no model turn in
between. When the attempts run out, the model is told to retry after 30 seconds
with the same arguments. The model's own retries stay bounded by the agent's
limits or the executor's fill and revision limits.

A tracker timeout after dispatch looks the same whether or not the write
committed. In Part B I simply stopped on it rather than retry blind; Part C adds
stable keys and read-back, so a write is retried only when it is confirmed
absent, and an unknown outcome escalates. The harness never reads the tracker's
internal `attempts` table to make that decision.

### No-token verification (Task 5)

- `python -m eval.errors_03` directly calls the registry with an unknown tool,
  a malformed number and `src/report.ts`. Reproducible outputs are in
  `runs/part-b-errors.json`; protocol details are in
  `runs/part-b-errors.harness.log`. It uses an isolated temporary tracker and
  asserts that no comments or PRs are written.
- `python -m unittest eval.test_errors_03`: **17 tests passed**, covering logging,
  non-object requests, repair facts for all tracker tools, the three near matches,
  error caps, transient recovery/exhaustion/backoff, explicitly unsent write
  retry, and both real tracker timeout outcomes without blind retry. Tests also
  show semantic faults are not retried, implementation details stay private,
  and both execution paths stop on interface errors.
- `python run.py --way agent --backend harness.scripted:UnknownToolCaller
  --issues 4191 --jobs 1` produced
  `runs/agent-4191-s01-6cb510.jsonl` and its harness log. The trace has one model
  call and ends `tool_error`; the full unknown tool name is in the private log.
  The 2994 reported tokens are scripted estimates, $0 actual API cost.
- `make test`: 58 passed, 2 starter-only skips. Part A/B contract tests: 28
  passed. `make check-03`: Error contract **10/10**.

## Part C · Writes that may already have happened

### Plan, draft and skip (Task 1)

`ways/planned.py:schema_check` requires exactly one PR step right before exactly
one comment step, which is last, for both new plans and revisions. The planner and
reviser prompts both state this order. Before the PR step, the executor drafts the
comment, runs the second pass on it (skipped when critique is off) and keeps the
result. If the second pass holds the draft, the run ends escalated with no writes.
The PR body names the file from that draft, and the comment step posts the same
draft unchanged.

I skip the PR with **a check in the executor**, without changing the plan schema.
If the draft's file is none, the executor marks the PR step done, logs
`pr_skipped`, makes no PR call, and goes on to post the comment. I tested this with
`DraftNamesNoFile` and critique off (with critique off, nothing rejects its
bug/none draft, which is what the test needs).

### Key formula (Task 2)

```python
canonical = json.dumps(
    {"run_id": run_id, "plan_step": plan_step, "arguments": arguments},
    sort_keys=True, separators=(",", ":"), ensure_ascii=False,
)
key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

The registry gets plan_step from ctx.call_tool. The arguments are validated and
normalized before hashing, then frozen, so every attempt sends a copy of the same
values with the same key. The key is never in a definition the model sees, and the
tracker enforces its uniqueness. A new run_id gives a new key, while the same run,
step and arguments always give the same one.

### Checks, verification and exits (Tasks 3–4)

The write loop is in `tools/writes.py` and makes at most 3 attempts. Before each
attempt it runs the hooks and a check scoped to the run: PRs by open branch,
comments by key. If the write already exists, it returns that row in the same
format as a new write. After a failure it reads the effect back. Found: carry on
with the existing row. Absent: retry with the same arguments and key. Read fails:
raise `WriteOutcomeUnknown`, which the executor turns into
`terminal_reason: escalated`. A write still unconfirmed after the third attempt
also escalates, and a failed PR means no comment is posted. A semantic error goes
back to the model with its repair fact instead of being retried unchanged.

### Independent record and hooks (Task 5)

The registry writes one line through ctx.calls.write for every attempt of every
call, reads and retries included, and also for protocol errors, rejected arguments
and denied calls. Reads have a null key, cost_usd is 0, and the result summary is
at most 300 characters. A timed-out attempt is recorded with is_error=true even
when the read-back later adds an ok line for it, so every tracker write matches an
ok or timeout line with its key.

Hooks get a copy of the arguments. Returning None allows the call; any other value,
False included, denies it. A hook that raises denies the call, and the exception
goes to the private log. Hooks run again before every retry. A real comment
timeout line from
`runs/planned-4191-s03-547e5d.calls.jsonl`:

```json
{"run_id": "planned-4191-s03-547e5d", "t": 8.461, "tool": "tracker_post_comment", "role": "comment", "args": {"number": 4191, "body": "label: docs\nfile: README.md"}, "plan_step": 5, "key": "a01ced28413139633aaf6fa35aa40f068fc4c3a6e4a50636aab8bf3272d925f6", "attempt": 1, "outcome": "timeout", "is_error": true, "result": "the tracker did not answer in time", "latency_s": 0.001, "cost_usd": 0.0}
```

That run's PR timed out on attempts 1 and 2 and succeeded on attempt 3, using
identical arguments and key throughout. Its comment timed out after committing;
the record above is followed by an ok record for attempt 1 with the same key,
without a second comment write.

### Control switches (Task 6)

KEY_MODE=uuid sends a fresh key on every attempt; VERIFY=off skips the read-back
and retries blind. The check before each attempt, the hooks and the three-attempt
limit stay on. In one scripted test, a PR committed and then timed out, and the
next attempt's branch check found it. The comment also committed and timed out,
but the new key missed it, so the control left 2 comments and 1 PR. With the
switches unset, the same kind of test leaves exactly 1 of each.

### Development verification (Task 7)

Local tests: `python -m unittest eval.test_writes_03` passed **15 tests**, including
the checker's three fault scenarios, canonical key stability, repeated invocation,
no-file skip, held/accepted second pass before writes, three-attempt exhaustion,
unavailable precheck, hook exceptions/denials/retry checks, and independently
recorded protocol/boundary/read attempts. A lost connection after commit with
failed readback also leaves a matching timeout record. The combined A/B/C suite
passed **43 tests**; course tests passed 58 with 2 starter-only skips.

Real dev commands (critique off, 3 sweeps of the 2 development issues):

```bash
FLAKY_WRITES=1 python run.py --way planned --set dev --runs 3
FLAKY_WRITES=1 READBACK_FAIL=1 python run.py --way planned --set dev --runs 3
```

| run_id | READBACK_FAIL | End | Comments | PRs | Timeouts |
|---|---|---|---:|---:|---:|
| `planned-4191-s01-5c7de7` | false | completed | 1 | 1 | 0 |
| `planned-4191-s01-83d7c9` | true | escalated | 1 | 1 | 1 |
| `planned-4191-s02-2263ee` | false | completed | 1 | 1 | 0 |
| `planned-4191-s02-53f217` | true | escalated | 0 | 0 | 1 |
| `planned-4191-s03-547e5d` | false | completed | 1 | 1 | 3 |
| `planned-4191-s03-b735ac` | true | escalated | 0 | 1 | 1 |
| `planned-4192-s01-3f077d` | true | completed | 1 | 1 | 0 |
| `planned-4192-s01-4899ca` | false | completed | 1 | 1 | 1 |
| `planned-4192-s02-4f4953` | false | completed | 1 | 1 | 2 |
| `planned-4192-s02-7bcf01` | true | escalated | 0 | 1 | 1 |
| `planned-4192-s03-1661a1` | false | completed | 1 | 1 | 1 |
| `planned-4192-s03-632d84` | true | escalated | 0 | 1 | 1 |

Normal flaky dev: all 6 completed, each with exactly one comment and one open PR;
7 timed-out write attempts recovered. It used 89762 tokens and $0.041207.
Readback-fail dev: 5 of 6 escalated after a timeout, while one encountered no
write timeout and completed. Three committed PRs with unavailable verification
left no comments; one pre-commit PR timeout left no writes; one committed comment
could not be confirmed and remained as a single comment. No duplicate writes
occurred. It used 81993 tokens and $0.035689. Combined real development spend was
171755 tokens and $0.076896, not the Part D measurement.

Additional free persistent runs: `planned-4191-s01-88d797` and
`planned-4192-s01-956543` (DraftNamesNoFile) completed with one comment and no PR.
`planned-4191-s01-873e33` and `planned-4192-s01-1ca017`
(DraftNamesMissingFile, critique external) escalated with zero writes.

`python -m eval.verify_writes_03` checks these 16 dev runs against the tracker
and the call records (counts, matching keys, draft order, no comment after a
failed PR) and writes `runs/part-c-verification.json`. The write counts come from
database rows, not from what the agent reported. It does not check whether each
triage answer is right; that is the separate grounded check.

## Part D · Measure

### Protocol and reproducibility

Starter commit: `a2936d70c7fe7b2802fff71daa3a8bf343850443`. I committed the
predictions on their own as `5e144f6` and pushed them at 04:17, before the first
flaky eval run at 04:24. The surface-counting script and its results are in the
commit before (`fee8e93`), and the Part A–C code is in `65d21ce`.
`reports/EVALUATION_03.json` records the prediction commit, a hash of the runtime
code before and after the runs, the one reset, the run IDs and the budget. I did
not change the code, model, settings or pricing between the token counts and the
two arms. Afterwards I only changed the summary and report scripts, and I did not
discard or rerun any evaluation.

After pushing the predictions I ran `make reset` once, which archived the dev
database to `tracker/archive/tracker-20261026-042409.db`. Then:

```bash
FLAKY_WRITES=1 python run.py --way planned --set eval --runs 2
FLAKY_WRITES=1 KEY_MODE=uuid VERIFY=off python run.py --way planned --set eval --runs 2 --start-sweep 3
```

Each arm has 12 finished runs: six issues twice, experiment sweeps 1/2 and control
sweeps 3/4. Both used gpt-4.1-mini, critique off and the same runtime. The two
write switches were the only configuration changes; readback_fail stayed false.
There was no reset between arms. Runtime fingerprint:
`bc8fbf9c6a84fe43cfe07117d303f3477dc0e6147684729bc664ada1e4ab0dd3`.

### 1. Surface tokens and mean-run price

`python -m eval.surface_03` sends the same one-message request with and without
each thing being counted. The bare request costs 33 prompt tokens, and each value
below is the API's prompt_tokens (cached included) minus that baseline. My
definitions are taken from `registry.schemas`, examples included. The starter's
are read from the initial commit with only the `tools.SENT` fields it had, and no
examples. The planner's tool-list formatter is the same function in both versions,
so I applied it to each set of definitions.

| Surface (actual prompt-token difference) | Starter | Current |
|---|---:|---:|
| Five tools together | 191 | 2042 |
| `read_issue` alone | 37 | 266 |
| `search_repo` alone | 71 | 624 |
| `read_file` alone | 34 | 348 |
| `post_comment` alone | 44 | 362 |
| `open_pr` alone | 53 | 490 |
| Planner/reviser text list | 106 | 1422 |

Raw usage and hashes are in `reports/SURFACE_03.json`. The 15 real counting
requests used 6585 prompt + 27 output = 6612 tokens and cost $0.002677; all are
charged to runs/_ledger.jsonl. The individual tool counts include one tool-use
preamble each; they must not simply be added to infer a combined request.

The harness arm has **87 model calls / 12 runs = 7.25 calls/run**, range 5–10.
There were 31 planner/reviser calls (13 plan, 18 revise), 27 search fills,
11 file fills, 12 comment drafts and 6 PR fills. submit_plan is unchanged and
excluded. Actual carried definition totals therefore are:

```text
Starter = 31×106 + 27×71 + 11×34 + 12×44 + 6×53 = 6,423 tokens
Current = 31×1422 + 27×624 + 11×348 + 12×362 + 6×490 = 72,042 tokens
All-five counterfactual = 87×2042 = 177,654 tokens
```

Divide each by 12 runs, then multiply by the retained **uncached input rate
$0.40 / 1,000,000 tokens** from pricing.yaml:

| Mean surface-only cost, n=12 harness runs | Starter carried | Current carried | Current five on every call |
|---|---:|---:|---:|
| Mean tokens/run | 535.25 | 6003.50 | 14804.50 |
| Uncached USD/run | $0.0002141 | $0.0024014 | $0.0059218 |
| Token range across runs | 308–768 | 3246–8760 | 10210–20420 |

Sending one tool per fill call saves $0.0035204/run, **59.45%**, compared with
sending all five on every call (that column charges all five and no tool list on
every call). My surface costs about 11 times the starter's per run. The extra
tokens spell out literal vs. glob matching, how a valid empty result differs from
an error, the result fields, the caps and the examples. They made failures visible,
but they did not make the model's choices correct, as the results below show.
These are definition costs only, not whole-run costs. Caching would lower the bill,
not the room the definitions take in context.

### 2. Writes counted from SQLite

`python -m eval.summarize_03` picks the formal runs by eval issue, finished status
and the switches they recorded. It opens `tracker/tracker.db` read-only, reads the
comments, prs and attempts tables by run_id, matches each write to a call-record
line by key, and counts committed timeouts as attempts with
`outcome = timeout_after_commit`. Escalations come from each trace's
terminal_reason. Triage success uses my grounded check (exactly one comment,
matching the fixture's answer), not what the run claimed. Per-run detail is in
`reports/MEASUREMENTS_03.json`.

| Measure | Harness, n=12 | Control, n=12 |
|---|---:|---:|
| Triage comments/run (mean; range) | 1.00; 1–1 | 1.75; 1–3 |
| Total triage comments | 12 | 21 |
| Runs with duplicate comments | 0/12 | 7/12 |
| Extra comment rows beyond one/run | 0 | 9 |
| Open PRs/run (mean; range) | 0.50; 0–1 | 0.4167; 0–1 |
| Total open PRs | 6 | 5 |
| PR count/branch matches first comment's file | 12/12 | 12/12 |
| Extra duplicate PRs | 0 | 0 |
| Writes that timed out after committing | 11 | 14 |
| Runs ended escalated | 0/12 | 3/12 |
| Grounded triage success | 3/12 (25.00%) | 1/12 (8.33%) |

All 12 harness runs left exactly one comment. In the control, five runs left one,
five left two and two left three. In both arms every run had one PR when its first
comment named a file and none when it named none. That measure follows what the
comment says, not the answer key, so a wrong label or file can still have correct
write counts: some feature/none and wrongly labelled question/none comments
skipped the PR. Safe writes are not the same as correct triage.

All three control escalations exhausted the three comment attempts:
`planned-4201-s03-ae2e69`, `planned-4204-s03-147ed5`,
`planned-4205-s03-5aff4f`. They left 2, 3 and 3 comments. In the last two, all
three attempts committed and then timed out, each under a different key, so the
run escalated even though its last comment had in fact landed.
`runs/planned-4205-s03-5aff4f.calls.jsonl` shows comment attempts 1, 2 and 3 as
timeouts with three keys, and the database holds three rows. My harness reads the
comment back under its stable key instead. The control still left no duplicate
PRs, because its branch check before each attempt finds a PR that already
committed, whatever the key.

Formal runs used 156209 tokens/$0.074645 in the harness and
150422 tokens/$0.068408 in the control: **306631 tokens/$0.143053 total**.
These are full-run charges, with output and any cache discount, unlike the
uncached definition-only arithmetic above. The whole ledger is at 627625 real
tokens, under the 3500000 ceiling (scripted runs excluded); I did not need
`--over-budget`.

### 3. Four shapes of misuse, with run evidence

**Right tool, wrong arguments: narrowed for structure, not for meaning.** No
formal run sent a malformed query, glob or enum value (Part A's tests show such
calls are rejected before dispatch). The arguments that went wrong were
well-formed but wrong: across the 24 runs there were 7 `code_read_file` errors (4
harness, 3 control), all guessed paths that do not exist. In
`runs/planned-4202-s01-73d402.jsonl` the model asked for
`src/export/ReportExport.ts`. The error named the near matches instead of
returning a wrong file, but the run still posted feature/none. Query choice was
also weak: for 4204, pasting a whole sentence from the issue kept returning zero
hits. These runs do not compare my surface with the starter's, so I can't say how
much the rewrite reduced this.

**Wrong tool, valid call: narrowed.** During a fill, the executor offers only the
step's tool. All **110 fill requests across the 24 runs** carried exactly one tool,
and there were no off_plan events; e.g. `runs/planned-4201-s01-62cae5.jsonl`
offers `code_search` for the search step and then `code_read_file` for the chosen
path. I saw no clear wrong-tool call, so I have no rate to compare. A bad plan
could still pick a valid but wrong tool, and zero off_plan events would not show
it.

**Correct call, misread result: easier to see, not fixed.** The result now tells
an empty match apart from a bad query, but the model still has to draw the right
conclusion. In `runs/planned-4203-s02-872332.jsonl`, a search for "Malformed row"
returned count=1, query_valid=true and one hit in `src/i18n/en.json`. The run read
that translation file and posted question/none, although the issue says every
upload fails and the answer is a parser bug. In
`runs/planned-4206-s01-12050f.jsonl`, three searches came back count=0,
query_valid=true, and the model then guessed an export file and blamed it instead
of finding the ingest code. I can see from the trace that the conclusion was
unsupported, but not why the model reached it. Each arm had 16 zero-hit searches;
I did not count them as misuse, since an empty result can be the right answer.

**No call at all: the one still standing.** I did not see it at the level of a
whole run: all 24 runs read their issue and searched, and every fill reply made
its call. But the planned way forces those calls, so this says nothing about how
often a free agent skips a tool, or about MCP-Atlas's 36%. The quieter version did
happen: most failed runs never read the file that was actually responsible,
because no step looked for it. I could not have detected that from errors or run
status, since those runs completed without any. To catch it I would need tasks
labelled with the calls they require, and compare those labels with the tool_call
records (Assignment 7's job). A better definition cannot help a tool the model
never calls.

The two arms differ only in the write switches; they do not compare the old and
new surfaces. The model's choices differ between runs (no fixed seed), so I do not
read the 3/12 vs. 1/12 success gap as better reasoning. Part of it is that a
duplicate comment fails the grounded check even when the first comment is right.
Critique was off, so nothing stopped an inconsistent label or an unsupported file.
I did not tune or rerun anything after seeing these results.

### 4. Predictions checked, including misses

| Prediction | Harness predicted → observed | Control predicted → observed |
|---|---|---|
| Extra comments | 0 → 0 | 9 → 9 |
| Duplicate-comment runs | 0 → 0 | 6 → 7 |
| Extra PRs | 0 → 0 | 0 → 0 |

**Miss 1: control duplicate-comment runs, 6 predicted, 7 observed.** I worked out
the prediction from the tracker's fault rates, assuming every run reached the
comment. The total of extra comments came out exactly as predicted (9), but they
spread over 7 runs (five with two comments, two with three) rather than 6. With 12
runs, how timeouts fall across runs is mostly luck, so the total can match while
the run count misses. My predictions for the harness (no duplicates) and for PRs
in both arms (no duplicates, because of the branch check) matched the tracker.

**Miss 2 (partly): most-misused tool.** I predicted `code_search`, expecting
valid but poor queries (issue sentences, globs narrowed too early) and empty
results read the wrong way. That kind of misuse did happen, as the examples above
show, but by errors the most misused tool was `code_read_file`, with 7 against 0.
What I missed is where a weak search shows up: a search that finds nothing is not
an error, so the model guessed a path instead, and the guess failed in
`code_read_file`. I can't confirm the search half of the prediction, because the
traces have no labels saying which queries were bad, and I did not count all 32
empty searches as misuse to make it look right.

### Reproduction and completion status

```bash
python -m eval.summarize_03
python -m unittest eval.test_tools_03 eval.test_errors_03 eval.test_writes_03 eval.test_measurements_03
make test
make check-03
```

My Part A–D tests come to 51 (8 of them for the measurement scripts), and the
course tests give 58 passes and 2 starter-only skips. `make check-03` gives
**82/82** automated points with no integrity flags. The Part C dev runs are in the
archived database, which `eval.verify_writes_03` reads without changing it.

## AI assistance

I used Codex to write most of the code: the five definitions and the boundary
check (A), the error routing, repair facts and retries (B), the plan order, keys,
write gate, call record, hooks and switches (C), and the counting scripts in
`eval/`, the tests and a first draft of the predictions and this report (D); I
 manually edit the report's wording. I checked the work with
`make test`, `make audit`, a real `make ping`, the local contract tests (51),
`make check-03`, and by reading dev and eval traces, call records and tracker rows
myself. I committed and pushed the predictions myself before the first eval run.
