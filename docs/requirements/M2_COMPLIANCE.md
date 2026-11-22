# Milestone 2 compliance audit

Audited November 22, 2026 (America/New_York). Source: [verbatim user-supplied requirements](M2_REQUIREMENTS.txt); provenance: [M2_SOURCE.md](M2_SOURCE.md). This audit checks the local working tree, not a final submission tag. M1's [compliance record](COMPLIANCE.md) remains historical.

**Overall: Part 2 policy, per-action approval, escalation holds and stop/compensation foundations are implemented; M2 implementation and evaluation remain incomplete.** See the current [Part 2 task checklist](PART2_CHECKLIST.md). A page, callback or test helper inherited from the starter is not evidence that the corresponding M2 behavior works. No M2 completion score is asserted.

## Requirement-by-requirement review

“Foundation” means related M1 behavior exists but the new acceptance tests are missing. “Missing” means the reviewed code does not implement the required behavior. “Pending” means evidence or a decision still needs to be produced.

| Requirement | Current evidence | Status | Required update and acceptance evidence |
|---|---|---|---|
| M1 verdicts retained | switches.yaml; LEDGER.md Pass 1 | Foundation | Start M2 at these settings, especially plan.batch=off; new switches need added: with their introduction date |
| State lifetimes and three-zone diagram (P1.1) | M1 state inventory; effects in sandbox/course.py; _last and locks in service.py | Foundation | Distinguish run state, later-session memory and crash persistence; draw app/runner entry, operator and outside channels, registry and MCP |
| Checkpoint placement and per-run durability modes (P1.2) | planning.py has logical validation checkpoints, not durable recovery | Missing | Mark every step read/keyed/unkeyed; justify placements, sync/async/exit; durable run keys include session + run number in app |
| Serialized checkpoints and completed-call journal (P1.2) | Trace and effects persist; active executor/model messages remain in memory | Missing | Save validated plan, current step/status, saved call arguments, keys/results/findings; export final checkpoint to trace; explicitly describe chat retention |
| Three exits on unknown writes (P1.2) | tools.py readback; ambiguous error halts; manual send can stay uncertain | Foundation | Confirmed: reuse; absent: same-key retry; unknown: durable escalation. Cover crashes during an in-flight write, not just normal returns |
| Recovery, compensation and irreversible-last ordering (P1.2) | Stable effect keys, manual discard/restore; no replay coordinator | Missing | kill -9 after last write commits on every writing task, resume same ID in a new process; save before/crash/resume sandbox snapshots; no completed call repeated |
| MCP server and SDK (P1.3) | Registry dispatches local handlers; requirements.txt has no MCP SDK | Missing | All registry calls reach server; fixed list order, explicit IDs/key, isError vs JSON-RPC error; stateless design; SDK/revision/read date and strict request evidence |
| Definition bill per agent/call/run (P1.4) | M1 three-call measurement; 808 rewritten overhead tokens | Foundation | Use actual M2 tools/calls/run count, window share and split roles; historical HW3 counts are separate evidence |
| Deferred loading (P1.4) | Fixed full model-facing list | Missing | Build catalogue search even if verdict is all; tools.loading: all/deferred; test first/next offerings, empty searches and miss logs |
| Sandboxed code calls (P1.4) | No program executor | Missing | Build closest use case even if off; code_calls.<case>; registry on every call, no intermediate context, restricted filesystem/network and repairable errors |
| Outside ask/wait/reply (P1.5) | on_outside_reply returns empty Reply; channel UI exists | Missing | Code detects missing required fact, template/model question authority; keyed send, Reply(waiting_for), durable wait/deadline and labelled reply; restart test through harness.turns.outside_reply |
| Per-call context assembly (P1.6) | bounds.py limits cumulative tokens/steps/time, not assembled input size | Missing | context_budget includes definitions/output reserve; priority and atomic tool pairs, omission trace, provenance; applied on every path |
| Notes/compaction and long sessions (P1.6) | No notes/context assembler or tasks/sessions | Missing | Protected current request, external notes, clear stale tool results first, bounded threshold, notes excluded from planner; long-session environment checks |
| Memory and later sessions (P1.7) | Effects persist; no independent provenance memory store | Missing | Four-part write policy, source/time/derived-or-ingested/confirmed, supersession and eviction; outside words unconfirmed; new-process session and contradiction tests |
| Orchestration verdict and boundary inventory (P1.8–9) | M1 workflow/agent split and state table | Pending | Four abstraction questions; supervisor/journal/checkpoint gaps; one row per fact across attention/compaction/session/restart |
| A2/A4 citations (P1) | A2 archive exists; A4 explicitly excluded from M1 | Pending | A2 notes vs compaction and A4 kill matrix/boundaries with owner/repo/numbers; historical evidence is not a current recovery test |
| Action ranking and policy file (P2.1–3) | policy/autonomy.yaml, hook.py, state.py; docs/requirements/PART2_POLICY.md; 12 new tests | Implemented foundation | Three-column classes, ranked actions, stop-first enforcement, per-attempt checks and persisted operator limits work. Per-action gate now implemented and tested; automated send classes are now implemented; full task-continuation integration remains pending |
| Computed approval screen and durable gate (P2.4) | policy/approvals.py; service callbacks; HTTP template; 15 approval tests | Implemented per action | Exact saved arguments/key, computed facts and original session survive restart; approvals recheck policy, outside text cannot approve. External-send gate is now implemented; general Part 1 task continuation remains pending |
| Plan/per-action approval (P2.4) | Plan support exists, default off | Missing | Justify both cases; fixed approved recipient/text/arguments, revisions and unlisted actions re-gated; output checks and skipped-step timing; dated approval switch |
| Queue page (P2.4) | sandbox/queue.py plus shared pending approval service | Foundation extended | Pending gates and executing/uncertain/blocked gate outcomes now visible; unchanged-before-approval and new-process execution tests pass. Escalated/over-cap/stopped work is now shown and tested. Durable Part 1 outside waits and full continuation remain pending |
| Escalation (P2.5) | policy/escalations.py; registry/service/planner and queue; 14 tests | Implemented hold/inspection; integration partial | Named signal, three-field packet, durable hold/deadline, shared daily cap and confirmed-effect settlement in a new process/session work. Full Part 1 task checkpoint, absent-effect retry and remaining-step continuation pending |
| Stop and cancel/resume/rollback (P2.6) | policy/controls.py; bounds/registry/service/hook; 13 tests; STOP_CHECK.json | Implemented control foundation; integration partial | Immediate stop, saved calls, withdrawn/reissued approvals, cancel, reverse compensation and five live probes work. Full Part 1 checkpoint/model/plan/outside-wait continuation remains pending; in-flight work cannot be preempted |
| Mid-task messages (P2.7) | policy/messages.py; service dispatcher; Bounds.model; 17 tests and two fixed_run fixtures/checks | Implemented live paths; integration partial | Explicit add/replace, eight-slot default FIFO, immediate reject, pre-model observation, effect listing/selected compensation and fresh run keys work. Persisted outside-wait/crash continuation still requires Part 1 |
| Disclosure and legal/framework analysis (P2.8–9) | PART2_DISCLOSURE.md; PART2_LEGAL.md; 16 disclosure tests; actual send review appendix | Task 8 implemented for current scope; task 9 partial | Code adds final line before review; hook rejects omission; independent outgoing checks; dated primary legal sources. Framework and real-human attention analysis remain open |
| Reviewer workload and A5 citation (P2) | No M2 human approval sessions or A5 results cited | Pending | Real-day asks with n, seconds/ask, actual human times/rates by action class vs scripted; plan-review savings and stop latency from named A5 source |
| Topology inventory/gates and A6 citation (P3.1–3) | Single-agent main; no topology record | Pending | Pairwise communication sketch; gates in order per component; measured A6 multiplier/matched-budget result; testable benefit and reopening condition |
| Split implementation and checks (P3.4) | Only local main branch listed; no split roles | Missing | After P2, m2-split coordinator + >=2 tool-separated roles even if gates fail; return schema first; call-derived coverage/spend, shared budget, end-state/divergence tests, parent traces |
| Decision and branch delivery (P3.5) | decisions/0006-topology.md absent | Missing | Main record; no merge without gates/tests/favourable equal-budget pass; otherwise tag m2-split-final and dated main single setting naming tag |
| M2 build runs and first failures (P4.1) | M1 baseline/dev/pass records only | Missing | All tasks including sessions/new M2 cases x3, switches at settings; first failure run+line, latency/cost/ask problems; at most 3 harder tasks if needed |
| Two new passes and analysis (P4.2–5) | LEDGER.md has M1 Pass 1 only | Missing | At least Pass 2 and Pass 3 from observed M2 failures; push prediction before either arm; same scripted answers, measures/run counts and total tokens; reproducible committed-results analysis |
| Report, ownership and submission | M1 report exists; no M2 report before this update | Pending | M2 build/decision tables, Parts 1–4, named owners, AI line, approval-screen appendix; ~2500 words for Parts 1–3 + team; clean clone/setup/app and final tests/check; branch/tag delivery |

## Required even when the design verdict is “off”

Build deferred loading, sandboxed code calls on the closest use case, and the split on m2-split. A negative gate verdict chooses the default; it does not waive these implementations. Main keeps the measured M1 settings until new evidence justifies changing them.

## Suggested implementation order

1. Durable run identity, checkpoint/journal, saved write calls and three-exit recovery. Add kill/restart tests before expanding outgoing writes.
2. MCP transport; durable outside exchange; per-call context assembly, notes/compaction and provenance memory. Build loading/code-call alternatives behind dated switches.
3. Code-enforced policy, durable computed approvals, held-run queue, escalation, stop/compensation and mid-task controls; common send disclosure.
4. After Part 2 works, build the candidate split on m2-split with contracts, shared budget and environment checks; write the main decision record.
5. Run m2-build over all tasks x3; record first failures. Run >=2 evidence-driven passes after separately pushed predictions, then finalize report, human review evidence and fresh-clone verification.

## Initial requirements-capture verification (historical)

Source inspection confirmed the stub callbacks in agent/service.py, local registry handlers in agent/tools.py, in-memory run state and lack of M2 switches/modules. The local project has no .venv. A diagnostic attempt used ../a3_57220_yaniw/.venv/bin/python (not a validated project environment): unittest discovered 91 entries and ended with 3 import errors because fastapi is absent; harness.check passed switches (46 records/13 switches), tasks (12 files) and ledger (1 entry), but failed app import for the same missing dependency. These outcomes do not establish a code regression or a passing suite. Run make setup, make test and make check in the project's own environment before claiming validation.

The initial requirements-capture update saved requirements and documentation only. Subsequent implementation increments and their tests are recorded below; those historical diagnostic failures do not describe the current installed environment.

## Part 2 policy implementation update — November 22, 2026

Yani Wu's first Part 2 increment adds [action ranking and policy evidence](PART2_POLICY.md), three-column rules, registry hook enforcement and code-parsed persisted operator limits. 12 focused policy tests pass. Unlike the initial audit environment, make setup has now installed the declared project dependencies in its own .venv. make test passed 114 tests and make check passed all four structural checks; details are recorded in PART2_POLICY.md. No M2 gate, full stop, Part 1 recovery, measured pass or submission claim follows from these policy tests.

## Part 2 per-action gate update — November 22, 2026

The [approval increment](PART2_APPROVALS.md) adds immutable saved calls, computed HTTP screens, atomic operator decisions, policy/source rechecks, original key/session execution, queue inspection and a scripted development task/check. 15 approval tests pass; the full suite passes 129 tests and make check passes with 13 tasks. Approval resumes one saved action, not all remaining task steps. Whole-plan approvals, sending/disclosure, escalation and full stop remain unfinished.

## Part 2 escalation increment — November 22, 2026

[Unknown-write escalation](PART2_ESCALATION.md) now persists an exact action packet, blocks later tools, shares the reviewer cap with approvals and exposes held/expired/over-cap runs. Trusted console inspection can settle a matching committed effect without replay; absent/unknown effects remain held for Part 1 recovery. Fourteen new tests and the updated planning regression pass; make test passes 143 tests and make check passes. This is not full task checkpoint/resume or the complete stop controller.

## Part 2 stop controls — November 22, 2026

[Stop evidence](PART2_STOP.md) documents immediate commands, durable action snapshots, approval withdrawal/reissue and policy-checked compensation. Thirteen control tests pass, including five measured live stops. Full suite passes 156 tests and structural checks pass. General resume remains awaiting_continuation for Part 1; stop cannot preempt an already-dispatched write or SDK request. The evidence file records the exact free-probe method and source hashes, not a real-model benchmark.

## Part 2 mid-task inbox — November 22, 2026

[Message handling](PART2_MESSAGES.md) now implements explicit add/replace, bounded default queue, rejection, selected old-effect compensation and original-run status answers. Seventeen message tests pass, including fixed_run/check_run end-state checks and a planted-old-write negative control. Full suite: 173 passed; structural checks pass. Live task extension/replacement works; restarted/outside-wait continuation remains joint Part 1 acceptance work.

## Disclosed-send increment

[Task 8](PART2_DISCLOSURE.md) now implements selected automated-send review, code disclosure, missing-line rejection, human-route bypass prevention and keyed delivery/readback. Sixteen free tests cover denial, concurrent/restarted approval and uncertain delivery. Full suite: 189 passed; four structural checks pass with 14 tasks. The [legal scope assessment](PART2_LEGAL.md) uses current primary sources; whole-plan review, reviewer attention/framework analysis and Part 1 integration remain open.
