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
