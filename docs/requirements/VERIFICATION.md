# Local verification, October 27, 2026

Engineering checkpoint tested: `0b18c90` on
`codex/milestone1-implementation`. The clone was a new Git checkout, not a copy
of an existing virtual environment or state directory.

| Command / action | Actual result |
|---|---|
| Initial `make test` | 44 passed, 0 failed |
| Initial `make check` | All four starter checks passed; application was still a placeholder |
| Final workspace `make test` | 75 passed, 0 failed |
| Final workspace `make check` | All four checks passed; 12 valid tasks, 13 switches, one explicitly pending ledger entry |
| `git diff --check` | Passed |
| Python compileall over application, checks, experiments and tests | Passed |
| `python -m experiments.analysis.summarize results/_free/local-smoke --include-free` | Recomputed retained JSON exactly: 30/30 free diagnostics |
| Same analysis without `--include-free` | Refuses free data (also verified by AnalysisTests) |
| `python -m experiments.analysis.tool_overhead --schema-only` | 0 enabled strict tools with defaults; candidate stats tested separately |
| `python -m experiments.analysis.tool_overhead` | Exited 2 before API calls: configure provider/model/key; no measurement file created |
| `git clone --no-hardlinks . /private/tmp/course-qa-m1-check-0b18c90` | Succeeded, clean checkout |
| Fresh clone `make setup` | Succeeded; created a new .venv and installed requirements |
| Fresh clone `make test` / `make check` | 75/75 passed and all four checks passed |
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
console trace is `traces/s-20261027-163105-fd85.jsonl`; its model calls use the
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
