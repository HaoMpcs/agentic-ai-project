# Milestone 1 requirement audit

Scope: the supplied Course Q&A Assistant master prompt, 2026-10-27. The authoritative
`milestone1-spec.md` and lecture slides are unavailable; this is a provisional audit,
not a replacement specification. Existing `docs/milestones/M1.md` is teammate work
and its eight use cases and approval boundary will be preserved.

Initial checkout: `main`, `83d10a8`, clean; implementation branch
`codex/milestone1-implementation`. No existing domain implementation or experiments.

| Requirement | Initial status | Existing code | Missing functionality | Verification planned |
|---|---|---|---|---|
| Authoritative specification | Missing | None | Official assignment and slides | User-provided source required |
| Core task, eight use cases, approval line | Partial | M1.md | Executable behavior and full risk grid | Tasks, environment checks, report |
| Deterministic sandbox and channel inputs | Missing | sandbox/seed.py, channel/ | Course records, private synthetic data, stamped effects | Sandbox and runner tests |
| Console and functional product page | Missing | agent/service.py, app/product.py | Routing, follow-ups, manual drafts/send/flags | HTTP and same-entry-point tests |
| Workflow and agent, grouped switches | Missing | switches.yaml | Trusted routing and bounded model loop | All routes, ambiguous input, never-stopping fake |
| Step, token, wall-clock limits | Missing | Harness ceiling only | Independent bounds and terminal reasons | Fake-model boundary tests |
| Plan, validation, revision, enforcement | Missing | Trace support only | Structured plan, checkpoint, detectors/diff | Bad plans, revisions, off-plan tests |
| Independent critique | Missing | None | Source-based bounded validation/revision | Correct, repair, reject, once-only tests |
| Central tool registry | Missing | Model/trace interfaces | Schemas, hooks, retries, keys, result bounds | Direct registry and fake-model tests |
| Five main tasks plus development task | Missing | tasks/example.yaml | Coverage for all eight use cases and batch | Runner plus negative-control checks |
| Real baseline, >=3 sweeps | Missing | Runner | Provider/model/key and real executions | Run records, traces, analysis |
| Improvement and pushed prediction | Missing | Ledger template | Evidence-selected hypothesis, push approval, arms | Ledger history and reproducible analysis |
| Assignment 1–3 evidence | Missing | None | Actual member measurements/repositories | Team input required |
| Technical report, tool/action tables, changes | Partial | M1.md, starter README | Implementation details and evidence | Final compliance report |
| Team ownership and collaborators | Partial | Names only | Confirmed responsibilities/access | Team/repository evidence required |
| Clean checkout and submission | Missing | Starter targets | Snapshot setup/app verification, disclosure, final commit/tag/push | Local snapshot; final actions reserved |

Implementation order:

1. Preserve starter interfaces; establish initial test/check results.
2. Build deterministic SQLite sandbox, synthetic sources, channel questions, effects.
3. Add registry, trusted workflow routing, source validation, bounded agent loop.
4. Add validated batch plans, checkpoint revisions and execution diff.
5. Add product operations, tasks and independent checks with negative controls.
6. Exercise error paths and fake models; fix issues; retain honest local traces.
7. Add analysis and model-overhead scripts, report, compliance and setup instructions.
8. Run full checks and clean-snapshot app test. Real evidence remains conditional
   on the external inputs above; never substitute fake runs for measured arms.
