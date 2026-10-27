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
- Post-baseline fixes: none; no official baseline has been run.

Reused starter: https://github.com/ralmhana/agentic-ai-project, retained local
initial commit `5016c83`. `harness/`, `channel/`, `run.py`, the operator pages and
44 starter tests retain their contracts. Existing domain design in
`docs/milestones/M1.md` from `83d10a8` was retained and extended. No Assignment
1–3 code or measurements were available to reuse; no such reuse is claimed.
