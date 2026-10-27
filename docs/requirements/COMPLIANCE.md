# Milestone 1 compliance and remaining work

Status: **Partially complete**. The implementation runs locally. This audit uses
the user's pasted requirements because the official milestone specification and
lecture slides are absent. It is not a score prediction or final submission
approval. `make check` checks starter structure, not the full academic rubric.

| Criterion | Points | Status | Implementation / documentation | Verification evidence | Remaining issue |
|---|---:|---|---|---|---|
| Clean checkout, make app, runner, make check | 3 | Verified locally | Makefile, app/, agent/service.py | 77 tests; runner smoke; VERIFICATION.md and clean-checkout-http.json | Real-model console and final submission commit |
| Three properties, channel, console, product page | 4 | Implemented/tested locally | sandbox/, channel/, app/product.py, home.html | CourseTests + ProductTests; manual operator send and uncertain-send tests | Official spec cross-check |
| Test tasks and independent checks | 4 | Implemented/tested | 10 main +2 dev YAML; checks/course.py | Every task via ScratchTest.run_task; negative controls via run_check | Real-model task performance |
| Routing, agent/workflows, traces, bounds | 5 | Implemented/tested locally | service.py, bounds.py, grouped switches | Misrouting, NeverStops, HugeUsage, SlowAgent; end reasons in records | Real latency; last response can cross token threshold; in-flight billing limitation |
| Planning and tests | 4 | Implemented/tested locally | planning.py | Valid/invalid/revision/off-plan/skipped/orphan/order tests; local-revision trace | Actual Assignment 2 and measured value |
| Critique and tests | 4 | Implemented/tested locally | critique.py, tools.py | Correct/repair/hold/once-only tests; repair and hold traces | Extractive-only; real-model utility |
| Registry, retries, keys, hooks | 5 | Implemented/tested locally | tools.py, sandbox/course.py | RegistryTests, same-key retries, first-result preservation, fail-closed hook | Provider/network behavior; no full M2 recovery |
| Rewritten tools and repairable errors | 4 | Implemented/tested locally | tools.py, docs/TOOLS.md, first_draft.json | Malformed calls, unknown tools, scopes, output bounds, fixed-order tests | Real-model failure taxonomy and measured definition benefit |
| Baseline measurements | 3 | Blocked | run.py and analysis script ready | 0 real runs; 30 fake smoke runs explicitly excluded | Provider/model/key and clean committed code |
| Improvement experiment and verdict | 11 | Blocked | PROTOCOL.md; pending Pass 1 in LEDGER | 0 off-arm, 0 on-arm real runs; no invented hypothesis/verdict | Baseline evidence, owner, numeric prediction, commit and authorized push before arms |
| Reproducible analysis script | 3 | Implemented/tested locally | experiments/analysis/summarize.py | AnalysisTests; local-smoke-v2.json recomputed from original records | Recompute actual baseline and both arms |
| Real task, use cases, independent criteria | 5 | Documented/implemented | M1 Part 1; original eight-case design retained | Tasks and environment checks | Official assignment confirmation |
| Baseline failures with IDs and trace lines | 6 | Blocked | M1 Part 4 has separately labeled free diagnostics | Real failures unavailable; retained fake failure lines cited accurately | Real baseline traces and diagnosis |
| Four gates and cost evidence | 9 | Partial | M1 four gates, symbolic break-even | Formula derivation; no numeric values invented | Actual Assignment 1 m/f/c/r; mistake value; real latency |
| Component control-flow classifications | 2 | Documented | M1 build table | Source inspection and path tests | Lecture slide numbers unavailable |
| Action grid, undo, approval line, trifecta | 6 | Documented/implemented | M1 action grid; docs/TOOLS.md | No publishing tool; manual review/send/status tests | Official criteria confirmation |
| Planning/critique decisions with evidence | 6 | Partial | M1 Part 2, decision and step-sizing tables | Fake plan/revision/critique traces, test names | Actual Assignment 2 and real experimental evidence |
| Execution-state awareness | 3 | Documented | M1 state inventory | Memory/trace/SQLite implementation and tests | No M2 continuation claimed |
| Complete tool table and contracts | 5 | Documented/implemented | docs/TOOLS.md and executable schemas | Registry tests; write verification inventory | Official criteria confirmation |
| Examples, strict, measurements, write verification | 5 | Partial | Selective switches, tool_overhead.py | Fixed-order/examples/schema-metrics/error/read-back tests | Provider strict support/limits/source-date and real overhead calls |
| Named team ownership | 3 | Pending confirmation | M1 The team | Names supplied; existing HaoMpcs commit preserved | Actual module/experiment/report responsibilities and account mapping |

Total rubric: 100 points (50 build/evaluation +50 documentation). No total score
is asserted. Passing structural checks does not resolve the rows marked partial,
blocked or pending.

## Verification record

- Initial checkout: main at 83d10a8, clean. Initial `make test`: **44 passed**;
  `make check`: all four checks passed on the starter (not feature completeness).
- Dependencies: `make setup` first failed because the restricted shell could not
  reach the package index; installing declared requirements with network access
  succeeded. No project dependency was added.
- Expanded suite: **77 passed, 0 failed**. Fresh clone at 0b18c90 completed
  make setup, 77 tests, make check, actual make app/HTTP console/manual-send
  verification and make serve persistence. See VERIFICATION.md. Free diagnostic
  arm records use the pre-commit code with dirty=true.
- Retained smoke: 30/30 free runs over ten tasks x3. Backend tests.fakes:GoodAgent.
  Recorded tokens are fake placeholders (3,900 input, 780 output); scripted
  price is $0. Median turn 0.002s, maximum 0.009s. These figures cannot establish
  real performance, token overhead, costs or routing economics.
- Additional retained free probes: revision pass 1/1, bad plan expected fail 0/1,
  critique repair pass 1/1, critique hold expected fail 0/1. M1 cites original
  trace line numbers. Zero real baseline/arm runs and zero real overhead calls.
- API key availability was checked by boolean presence only; no secret value
  was read into output. No configured provider/model and no relevant key exist.

## External completion dependencies

1. Supply the official `docs/requirements/milestone1-spec.md` and lecture slides;
   compare every requirement again. The audit file is not an invented spec.
2. Supply real member Assignment 1–3 measurements/repository references. Fill in
   cost gates, quantitative routing justification and lecture slide citations.
3. Confirm model/provider and configure the API key locally. Verify price and
   strict-mode support/limits from the selected vendor, with source/date.
4. Run real baseline, inspect failures, select one intervention, name its owner
   and prepare numeric prediction. Only then request permission for the required
   prediction push; no measured arms may precede it.
5. Confirm team responsibilities and required collaborator/course-staff access.
   Git remotes alone do not prove access. No collaborator list was fabricated.
6. The user must complete the course-required AI assistance disclosure at the
   end of M1.md in their separate stage. No section was created/populated and no
   checker was weakened. The starter checker does not enforce that disclosure,
   so its passing result cannot establish academic readiness.
7. After evidence and disclosure, run final checks, create the final milestone
   commit, repeat the final clean checkout, and obtain authorization before
   publishing tag `m1` or pushing commits/tags. Canvas requires the team's repo URL.

## Git and submission boundaries

Implementation branch: codex/milestone1-implementation. Existing teammate design
was retained. Local engineering checkpoint commits are distinct from a final
Milestone 1 submission commit. No prediction was pushed, no final `m1` tag was
created, and no remote push was executed. The existing origin is
`git@github.com:HaoMpcs/agentic-ai-project.git`; staff collaborator status is
unverified. Final repository URL: https://github.com/HaoMpcs/agentic-ai-project.
