# Milestone 1 compliance and remaining work

Current evidence update: M1 now includes Hao Shi's Part 1 gate analysis, the
real tool-definition measurement, a 30-run baseline (27 passed), and a completed
Pass 1 (plan on: 0/3; plan off: 3/3). The verdict keeps plan.batch=off. These
results supersede the missing-provider/baseline/pass entries in the earlier
audit; see M1 Parts 1, 3 and 4 and experiments/LEDGER.md. The table below now
reflects the retained evidence, but is not a score prediction.

Status: **Partially complete**. The implementation runs locally. This audit uses
the user's pasted requirements because the official milestone specification and
lecture slides are absent. It is not a score prediction or final submission
approval. `make check` checks starter structure, not the full academic rubric.

Source update, November 2, 2026 UTC: Jingyu Huang supplied Assignment 1-4 ZIPs.
Assignment 1-3 citations now appear in M1 Parts 1-3, with a retained source guide
in [ASSIGNMENT_EVIDENCE.md](ASSIGNMENT_EVIDENCE.md). Offline analysis verifies
256 source hashes and recomputes 216 historical runs from traces and tracker
records. These historical references remain separate from Hao Shi's gate
calculation and the project's own measured baseline/pass. Assignment 4
recovery/memory stays outside M1.

## Current requirement status

Historical verification details remain below the table with their dates. Current
experiment status comes from M1 Part 4, the ledger and retained results.

| Criterion | Points | Status | Implementation / documentation | Verification evidence | Remaining issue |
|---|---:|---|---|---|---|
| Clean checkout, make app, runner, make check | 3 | Verified locally | Makefile, app/, agent/service.py | 102 current tests; earlier 77-test clean checkout and HTTP record in VERIFICATION.md | Repeat clean checkout for the final tag |
| Three properties, channel, console, product page | 4 | Implemented/tested locally | sandbox/, channel/, app/product.py, home.html | CourseTests + ProductTests; manual operator send and uncertain-send tests | Official spec cross-check |
| Test tasks and independent checks | 4 | Implemented/tested | 10 main +2 dev YAML; checks/course.py | Every task via ScratchTest.run_task; 30-run real baseline | None for M1 evaluation |
| Routing, agent/workflows, traces, bounds | 5 | Implemented/tested locally | service.py, bounds.py, grouped switches | Misrouting, NeverStops, HugeUsage, SlowAgent; end reasons in records | Real latency; last response can cross token threshold; in-flight billing limitation |
| Planning and tests | 4 | Implemented/tested locally | planning.py | Valid/invalid/revision/off-plan/skipped/orphan/order tests; A2 evidence now cited | Current-domain measured utility |
| Critique and tests | 4 | Implemented/tested locally | critique.py, tools.py | Correct/repair/hold/once-only tests; repair and hold traces | Extractive-only; real-model utility |
| Registry, retries, keys, hooks | 5 | Implemented/tested locally | tools.py, sandbox/course.py | RegistryTests, same-key retries, first-result preservation, fail-closed hook | Provider/network behavior; no full M2 recovery |
| Rewritten tools and repairable errors | 4 | Implemented/tested locally | tools.py, docs/TOOLS.md, first_draft.json | Malformed calls, unknown tools, scopes, output bounds, fixed-order tests | Real-model failure taxonomy and measured definition benefit |
| Baseline measurements | 3 | Complete | results/baseline; M1 Part 4 | 30 real runs, 27 passed; tokens, cost and latency retained | None |
| Improvement experiment and verdict | 11 | Complete | LEDGER.md; results/pass1-plan-on and pass1-plan-off | Prediction pushed first; on 0/3, off 3/3; verdict keeps plan.batch=off | None |
| Reproducible analysis script | 3 | Implemented/tested locally | experiments/analysis/summarize.py | AnalysisTests; baseline and both pass arms recomputable | None |
| Real task, use cases, independent criteria | 5 | Documented/implemented | M1 Part 1; original eight-case design retained | Tasks and environment checks | Official assignment confirmation |
| Baseline failures with IDs and trace lines | 6 | Complete | M1 Part 4 | Three real batch failures cite first trace lines and answer the four plan questions | None |
| Four gates and cost evidence | 9 | Documented | M1 four gates and A1 citation | Hao Shi A1 gives m=3.72; assumptions and break-even are explicit | Values are estimates, not current-domain causal measurements |
| Component control-flow classifications | 2 | Documented | M1 build table | Source inspection and path tests | Lecture slide numbers unavailable |
| Action grid, undo, approval line, trifecta | 6 | Documented/implemented | M1 action grid; docs/TOOLS.md | No publishing tool; manual review/send/status tests | Official criteria confirmation |
| Planning/critique decisions with evidence | 6 | Complete | M1 Part 2, decision and step-sizing tables | A2 four arms x18; plan/critique choices, checkpoints, bounds, tests and inventory documented | None |
| Execution-state awareness | 3 | Documented | M1 state inventory | Memory/trace/SQLite implementation and tests | No M2 continuation claimed |
| Complete tool table and contracts | 5 | Documented/implemented | docs/TOOLS.md and executable schemas | Registry tests; write verification inventory | Official criteria confirmation |
| Examples, strict, measurements, write verification | 5 | Partial | Per-tool decision table, selective switches, tool_overhead.py | Real definition measurement; fixed-order, error and read-back tests | Criteria ask for one enabled helpful example; current evidence leaves every example off |
| Named team ownership | 3 | Complete | M1 Part headings and The team | Hao Shi: Parts 1 and 4; Jingyu Huang: Part 2; Yani Wu: Part 3 | None |

Total rubric: 100 points (50 build/evaluation +50 documentation). No total score
is asserted. Passing structural checks does not resolve the rows marked partial,
blocked or pending.

## Verification record

- Initial checkout: main at 83d10a8, clean. Initial `make test`: **44 passed**;
  `make check`: all four checks passed on the starter (not feature completeness).
- Dependencies: `make setup` first failed because the restricted shell could not
  reach the package index; installing declared requirements with network access
  succeeded. No project dependency was added.
- Expanded suite: **77 passed, 0 failed**. Fresh clone at aefe416 completed
  make setup, 77 tests, make check, actual make app/HTTP console/manual-send
  verification and make serve persistence. See VERIFICATION.md. Free diagnostic
  arm records use the pre-commit code with dirty=true.
- Retained smoke: 30/30 free runs over ten tasks x3. Backend tests.fakes:GoodAgent.
  Recorded tokens are fake placeholders (3,900 input, 780 output); scripted
  price is $0. Median turn 0.002s, maximum 0.009s. These figures cannot establish
  real performance, token overhead, costs or routing economics.
- Additional retained free probes: revision pass 1/1, bad plan expected fail 0/1,
  critique repair pass 1/1, critique hold expected fail 0/1. M1 cites original
  trace line numbers. These pre-evaluation probes are not the later measured arms.
- Later commits configured Gemini 3.5 Flash-Lite, measured tool overhead, ran the
  30-run baseline and completed both Pass 1 arms. No secret value was recorded.

## External completion dependencies

1. Resolve the Part 3 example requirement without contradicting the retained baseline and Pass 1 settings.
2. Confirm required collaborator/course-staff access.
   Git remotes alone do not prove access. No collaborator list was fabricated.
3. After the remaining evidence is complete, run final checks, create the final milestone
   commit, repeat the final clean checkout, and obtain authorization before
   publishing tag `m1` or pushing commits/tags. Canvas requires the team's repo URL.

## Git and submission boundaries

The implementation is now on `main`, and the prediction and measured Pass 1
commits are pushed to `origin/main`. No final `m1` tag has been created. The existing origin is
`git@github.com:HaoMpcs/agentic-ai-project.git`; staff collaborator status is
unverified. Final repository URL: https://github.com/HaoMpcs/agentic-ai-project.
