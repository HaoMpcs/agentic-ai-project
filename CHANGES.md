# Milestone 2 disclosed automated sends — November 22, 2026

Owner: Yani Wu.

- Added `/send EFFECT_ID`, code-owned AI identity/TA contact and exact final-message approval. The hidden send capability is restricted to the selected draft; omitted disclosure and invalid drafts are prohibited.
- Recorded draft authorship and blocked automated drafts from the manual send route. Added atomic target key/message storage and confirmed readback after uncertain delivery; sent effects have no rollback.
- Added 16 free disclosure tests, an independently checked development task and rendered review evidence. Full suite: 189 passed; make check passes with 14 tasks.
- Added dated primary-source legal applicability for the EU AI Act and Colorado/California. Whole-plan review, real-human evidence/frameworks and full Part 1 continuation remain open. No model API calls, commit or push.

# Milestone 2 stop controls — November 22, 2026

Owner: Yani Wu.

- Added immediate operator stop/cancel/resume/rollback commands before session
  locks; stops target all session runs or one supplied durable run ID.
- Added persisted call registration/results, control snapshots and atomic
  stop-check/dispatch registration. Model waits observe stops; late provider
  work cannot execute tools. In-flight effects finish and are recorded.
- Stop withdraws approvals; resume issues new approval IDs without accepting old
  answers. Cancel is permanent. Rollback compensates owned internal effects in
  reverse order through the policy hook, with audited stable keys and none for
  irreversible effects. No full task replay or budget reset is implemented.
- Added 13 control tests and a reproducible five-probe latency report. Full suite:
  156 tests passed; make check passed. No model API request or assignment runtime
  reuse. Complete task/outside-wait continuation still belongs to Part 1.

# Milestone 2 unknown-write escalation — November 22, 2026

Owner: Yani Wu.

- Added the named write_outcome_unknown signal, immutable saved-call packet,
  persisted hold/deadline and queue inspection. Later tools are blocked by the
  hook; workflow/agent/planner paths stop at escalated_held without retry/re-plan.
- Added a shared reviewer cap counting approvals plus notified escalations by
  America/New_York day; over-cap runs hold without an unsolicited packet.
- Added trusted console inspection and environment-verified confirmation from
  a later session/process. Confirmed effects are reused, absent effects remain
  awaiting Part 1 recovery, and unknown/mismatched outcomes remain held.
- Added 14 escalation tests and updated the planning regression to verify the
  persisted hold. Full suite: 143 tests passed; make check passed. No assignment
  runtime code reused, model API requests, measured arms or switch changes.
- Part 1's full checkpoint, absent-write same-key retry and task continuation,
  plus the full Part 2 stop controller, remain outside this increment.

# Milestone 2 per-action approval gate — November 22, 2026

Owner: Yani Wu.

- Added durable immutable approval requests with exact arguments/key, original
  session/run, source/input snapshots and runtime settings; wired the shared
  approval callbacks to the app and scripted runner.
- Added an exact-effect screen with computed scope/source checks and labelled,
  escaped student text; decisions log actor, facts, elapsed seconds and mode.
- Approval atomically claims a request and executes only its reviewed operation
  through the registry after policy/source/stop rechecks. Denial, duplicate
  decisions and changed authority cannot execute it. Unknown execution stays
  held for inspection; no automatic crash recovery is claimed.
- Extended queue inspection, added a development task and independent sandbox
  check, and added 15 approval tests. Full suite: 129 passed; structural checks
  pass. No model API requests or assignment runtime reuse in this increment.
- Whole-plan approval, external sends/disclosure, full stop/escalation and Part 1
  continuation remain separate work; existing model settings/switches unchanged.

# Milestone 2 Part 2 policy foundation — November 22, 2026

Owner: Yani Wu.

- Added policy/autonomy.yaml, trusted-record action classification and policy
  enforcement before registry dispatch and every transport retry. Stop flags
  take precedence; unknown classes, invalid policy and hook exceptions deny.
- Added session-scoped SQLite operator restrictions, exact /limit commands and
  supported phrases parsed before model calls/session locks; sandbox reset
  clears control records. Outside messages cannot set rules.
- Kept additional registry hooks as restrictions; an always-yes hook cannot
  bypass a prohibited class. Approval-required calls halt without a write;
  durable approval/resume and full stop commands remain separate work.
- Added 12 policy/environment tests and the action-ranking/integration document.
  No Part 1 execution/checkpoint code was added or reused. No assignment runtime
  code was reused in this increment. Existing model settings/switches remain.

# Milestone 2 requirements and audit — November 22, 2026

- Added a verbatim copy of the user-supplied M2 assignment with a source hash,
  requirement-by-requirement implementation audit and working M2 report.
- Updated README links and distinguished M1 persistence from missing M2 durable
  continuation, approval/stop controls, MCP, context/memory and branch work.
- Removed no runtime behavior. Limited completion claims to inspected source
  and explicitly recorded diagnostic outcomes; no M2 measurement is asserted.
- No assignment or course runtime code was reused in this update. Existing M1
  code and measured switch settings remain the starting build. No M2 prediction,
  measured arm, split branch, submission tag or API request was created.

# Milestone 1 changes

- Added deterministic public course documents, prior public answers, synthetic
  private students, initial channel questions, a fixed clock, SQLite drafts/flags
  and audited manual operations under the starter's state directory.
- Implemented trusted-metadata routing for eight domain use cases and batches,
  fixed workflows, a bounded model loop, session follow-ups and staff summaries.
- Added a central registry with argument/content/result validation, response
  bounds, fixed ordering, fail-closed hooks, classified errors, bounded retries,
  run/session action keys and independent read-back of persistent effects.
- Added validated batch plans with runtime placeholders, a sources_available
  checkpoint, bounded revisions preserving the executed prefix, refusal of
  changed/off-plan calls, repeated-call detection and execution diffs.
- Added independent public-source critique with a three-attempt bound. Replies
  remain pending; only the operator can send on the product page.
- Replaced the example task with ten main tasks and two development tasks, with
  environment-based checks, negative controls and free fake-model tests.
- Replaced the placeholder product page with course sources, inbox, drafts,
  manual handling, sending, discard/restore and clear/reopen operations.
- Added reproducible analysis, a retained concise tool-definition variant, and a
  real-API overhead measurement command that refuses unconfigured/fake models.
- Restricted later outside replies and the approvals API to their M1 starter
  behavior. No automatic sends, private-data tool, durable task continuation,
  or M2 ambiguous-send recovery was added.
- Replaced flat starter switches with implemented grouped switches. Removed
  unused notes/self-critique choices and tasks/example.yaml.
- Verification fixes before any real baseline: exact topic matches take
  precedence over title keywords; checks inspect unexpected outgoing threads;
  arm analysis uses the starter's actual `task`/`settings` record fields and
  accepts model-free workflow runs within a configured arm. Late model calls
  mark billing incomplete in analysis rather than implying a known zero cost.
- Removed answer-signaling conflict metadata in the final review. An ordinary
  project_deadline topic now returns two source records with differing values
  for the same structured claim; a conflict flag requires observed source reads.
  The final smoke arm reruns every main task after this change.
- Preserved runner classification of harness token ceilings, provider daily quotas
  and exhausted rate-limit retries; configuration errors do not swallow these outcomes.
- November 1 execution fixes before any real baseline: replaced free-text plan
  expectations with six fixed, executable outcome contracts. The executor checks
  record identity, source properties and pending/open write states, traces each
  check, and halts on a mismatch rather than continuing the plan.
- Added the named draft_supported checkpoint for source-critic rejections before
  persistence. Only those typed failures may request a validated revision; they
  share the existing one-revision budget with sources_available. Completed steps,
  write identity, critique limits and the human-only send boundary are preserved.
  Generic errors and ambiguous writes do not enter the revision path.
- Centralized checkpoint/revision handling and the critique round constant;
  source facts are sorted once per review instead of once per matched sentence.
  Updated fake planners, isolated regressions, trace analysis and M1 contracts.
  These are engineering corrections, not a measured improvement pass.
- Pass 1 after the real baseline changed `plan.batch` from on to off. The plan
  arm passed 0/3 batch runs and the bounded-loop arm passed 3/3. Plan-specific
  tests now enable the switch explicitly so the mechanism remains covered.
- November 1 responsibility-2 verification: added eight routing, planner-input,
  executed-prefix, validation, placeholder, critique-feedback and token-bound
  contract tests. Added an opt-in report command which runs 43 scoped tests,
  exports unchanged free ScratchTest records/traces, fingerprints working
  sources and runs the full suite and structural checks. The scoped tests pass
  43/43 and the current full suite passes 99/99. See
  docs/requirements/AGENT_TEST_REPORT.md. No production behavior, model settings,
  tasks, checks or switches changed in this verification; no measured pass or
  real-model performance claim was added.

Reused starter: https://github.com/ralmhana/agentic-ai-project, retained local
initial commit `5016c83`. `harness/`, `channel/`, `run.py`, the operator pages and
44 starter tests retain their contracts. Existing domain design in
`docs/milestones/M1.md` from `83d10a8` was retained and extended. No assignment
runtime code was imported. Hao Shi's Assignment 1 measurements remain the
primary source for Part 1's gate calculation. Jingyu Huang's Assignment 1-3
archive reports and measurements are also retained and cited, from
`ylwhale/agentic-ai-assignment1`, `ylwhale/agentic-ai-assignment2` and
`ylwhale/agentic-ai-assignment3`. See docs/requirements/ASSIGNMENT_EVIDENCE.md
for hashes, archived revisions and recomputation. The offline evidence analyzer
and its tests are new code. Assignment 4 was reviewed for scope; its recovery
and memory code was not reused.

# Milestone 2 — Part A

Owner: Jingyu Huang (CNetID: jyhuang28).

- Added a SQLite run store, prepared/completed-call journal, saved model calls
  and plan/prefix/revision state, cumulative bounds, process/thread ownership,
  call-triggered resume and final checkpoint exports in traces.
- Added read-back resolution for confirmed, absent and unknown writes, stable
  per-run action keys, reverse keyed compensation and conservative staff holds.
- Routed valid Registry dispatch through a fresh request-scoped MCP SDK Server;
  pinned mcp 1.30.0, documented its 2025-11-25 protocol revision and the tested
  stateless compatibility adapter. Added no handshake or deprecated capabilities.
- Added deferred catalogue loading and a bounded Python-subset program process,
  both behind dated switches. All program calls retain Registry/hook/MCP checks;
  no general Python execution, file or network capability is exposed.
- Added a fixed-template, disclosed missing-topic question, a persistent external
  wait, exact offered-topic validation, timeout/unknown holds and a demo case.
- Added B's context and C's control/policy adapter contracts, without claiming
  notes, memory, approvals or a complete autonomy policy are implemented.
- Added free cross-process crash/wait/program tests, recovery evidence, analysis
  and English implementation/handoff documentation. Updated the M1 timeout test
  to require reuse after independent confirmation; an inconclusive-read test
  separately requires holding without another effect.
- Retained Jingyu Huang's Assignment 4 original reports from
  ylwhale/agentic-ai-assignment4 with hashes, citing its reported stable-key and
  broken-key matrices. No Assignment 4 runtime code, RepoMind fixtures/tools or
  recovery framework was imported. Continued our own M1 service, registry,
  executor and starter test harness; harness/, channel/ and run.py are unchanged.
- Deferred the full M2 baseline, topology branch and formal passes to integration;
  no prediction, performance improvement or measured experiment is invented.

# Milestone 2 — integration

- Integrated the durable Part A runtime/MCP/recovery work with Part 2 policy,
  approvals, escalation, stop, message and disclosure controls.
- Added per-call bounded context assembly, safe notes and later-session provenance
  memory with contradiction/supersession tests.
- Built the required two-role candidate on `m2-split`, including a schema-first
  return contract, shared budget, linked traces and planted-divergence checks.
  Equal free diagnostics passed 27/30 in both arms; the integration branch keeps
  `topology=single` because split added latency without an observed benefit.
- Froze the next-pass prediction in the ledger. Formal model runs are not claimed:
  they require a pushed prediction, configured credential and retained evidence.
- Added `approval.reviewed_send=plan|per_action`. Plan mode reviews the complete
  resolved read/check/send sequence once, authorizes only its exact listed calls,
  and re-gates any changed or additional send.
