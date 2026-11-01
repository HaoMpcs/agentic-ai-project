# Local verification, October 27, 2026

Final engineering checkpoint tested: `aefe416` on
`codex/milestone1-implementation`. The clone was a new Git checkout, not a copy
of an existing virtual environment or state directory.

| Command / action | Actual result |
|---|---|
| Initial `make test` | 44 passed, 0 failed |
| Initial `make check` | All four starter checks passed; application was still a placeholder |
| Final workspace `make test` | 77 passed, 0 failed |
| Final workspace `make check` | All four checks passed; 12 valid tasks, 13 switches, one explicitly pending ledger entry |
| `git diff --check` | Passed |
| Python compileall over application, checks, experiments and tests | Passed |
| `python -m experiments.analysis.summarize results/_free/local-smoke-v2 --include-free` | Recomputed retained JSON exactly: 30/30 free diagnostics |
| Same analysis without `--include-free` | Refuses free data (also verified by AnalysisTests) |
| `python -m experiments.analysis.tool_overhead --schema-only` | 0 enabled strict tools with defaults; candidate stats tested separately |
| `python -m experiments.analysis.tool_overhead` | Exited 2 before API calls: configure provider/model/key; no measurement file created |
| `git clone --no-hardlinks . /private/tmp/course-qa-m1-final-20261027` | Succeeded, clean checkout |
| Fresh clone `make setup` | Succeeded; created a new .venv and installed requirements |
| Fresh clone `make test` / `make check` | 77/77 passed and all four checks passed |
| Fresh clone `make app BACKEND=tests.fakes:GoodAgent PORT=8765` | Actual uvicorn server started on localhost |
| Actual HTTP console: SYN-Q-deadline | Workflow, persisted correct pending reply |
| Actual HTTP console: SYN-Q-concept | Fake model chose tools, read both sources, persisted supported pending reply |
| Actual HTTP console: SYN-Q-private | Workflow, fixed privacy refusal, no private-data lookup |
| Actual HTTP follow-up | Matched current session's previous question/effect |
| Actual HTTP product manual send, repeated twice | One operator-channel message; second request returned existing sent state |
| Actual HTTP six product/operator pages | All returned 200 and navigation |
| Stop server; fresh `make serve` without reseeding | Restarted successfully; 3 effects, 1 sent reply and exactly 1 operator message survived |

The shell sandbox initially prevented package downloads and loopback network
operations. The declared dependencies, server binding and localhost HTTP checks
were rerun successfully with the necessary sandbox permissions. Those initial
command failures were environment restrictions, not passed app tests.

The actual HTTP result is retained in `clean-checkout-http.json`. The original
console trace is `traces/s-20261027-163543-2971.jsonl`; its model calls use the
free `says-done` identity from `tests.fakes:GoodAgent`, not a real provider. No
real model or API-key behavior was verified. The trace records tool calls,
source critique and persistent effects; manual publication is independently
confirmed by the HTTP check's channel/SQL reads.

The unit suite's expected bad-plan and invalid-draft task failures are assertions
of safe refusal; they do not mean that the test suite failed. Separately retained
free probes have the same interpretation. All official baseline and improvement
counts remain zero. Future documentation-only commits do not change the tested
engineering code; repeat the final checkout once academic evidence and
submission artifacts are complete.

The earlier 0b18c90 checkout also passed its then-current 75 tests and HTTP/
restart checks. Final review subsequently replaced answer-signaling conflict
metadata with observed structured source claims, and added regressions for
source reads and preserved harness ceiling/quota outcomes. The final aefe416
checkout repeated setup, all **77 tests**, structural checks, actual HTTP
console/manual-send operations and restart persistence. The newer smoke arm is
`local-smoke-v2`: 30/30 pass, 3,900 input plus 780 output placeholder tokens.
The original local-smoke arm remains as historical free diagnostic data.

## Execution corrections, November 1, 2026

The working-tree update adds executable plan outcome contracts and the bounded
`draft_supported` revision checkpoint. The historical results above were not
rewritten and are not evidence for this update.

- `make test`: **90 tests passed**, including 13 added tests. New coverage uses
  free models in `ScratchTest` folders for wrong outcomes, successful and rejected
  draft revisions, preserved writes and idempotency keys, shared revision limits,
  unchanged privacy boundaries, uncertain-write refusal and trace recomputation.
- `make check`: all four structural checks passed.
- `git diff --check`: passed.
- No real provider calls, official baseline/arms, remote push, or final tag were
  performed. This update has no real-model performance or cost measurement.

## Responsibility-2 test report, November 1, 2026

The [scoped report](AGENT_TEST_REPORT.md) records 43/43 tests for routing,
Agent bounds, planning/checkpoints/diff, critique and related analysis. Eight
new contract tests bring the full suite to **98 passed**. `make check` and
`git diff --check` pass. The report command retains 69 free runner records with
their original traces and four direct session traces, plus the original logs
and working-source fingerprints. Negative task checks are expected refusal and
fault-injection observations, not failed unit tests. These are working-tree
results, not a new clean-clone check or a real-model improvement experiment.
