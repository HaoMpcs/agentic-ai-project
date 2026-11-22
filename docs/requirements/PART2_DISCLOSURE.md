# Part 2: disclosed, reviewed automated sends

Owner: Yani Wu. Updated November 22, 2026 (America/New_York). Implements task 8 for the current local Course Q&A capabilities. Legal applicability is assessed separately in [PART2_LEGAL.md](PART2_LEGAL.md).

## Ranked action and operator flow

First narrow the capability: the model still sees seven tools and cannot select a send. The trusted operator selects an existing automated pending draft with `/send EFFECT_ID` (or a question ID with exactly one such draft). Its original sources must remain valid. A send cannot be recalled, is visible to a student and affects one selected thread; `course_send_reply/student_reply` therefore requires per-action approval. Missing disclosure and invalid/stale drafts are prohibited. Operator restrictions can further deny sends; approval cannot override a prohibition.

`policy/disclosure.py` adds this final paragraph in code before the registry and before the approval is stored:

> This message was written by an automated AI agent. To reach a person, reply here and ask for the course TA.

The computed review screen shows the final body, selected thread, one recipient, draft authorship, current source records and the irreversible effect. Arguments, facts and action key are frozen. Approval rechecks sources, policy, stop state and the selected draft; denial sends nothing. The hook rejects a direct registry send missing the line. The handler independently checks the exact rendered body. The human contact instruction uses the existing thread; automatic outside-reply processing remains Part 1 work, so this line does not promise automatic routing or immediate TA availability.

Human-authored drafts retain the explicit manual send route and appear as operator messages. Authorship is recorded separately when a draft is created. Automated drafts cannot use that manual route; unknown legacy authorship also fails closed. Raw channel primitives remain infrastructure for fixtures and explicit human actions, not model capabilities.

## Delivery and uncertain outcomes

The send key is derived from the effect ID, not a new run ID. The local channel transaction atomically stores that key and its message; repeated identical keys return the same receipt, conflicting content is rejected. The course record and channel record use separate databases: an interrupted status update can leave an uncertain course record. Such outcomes enter the existing escalation hold. Readback must match the saved key, recipient, sender, final text and selected draft before metadata is confirmed; it does not send again. An absent receipt remains held for Part 1 same-key recovery. These properties apply to this SQLite channel, not an unimplemented external messaging service.

Sent effects have no rollback compensation. Stop can block a future dispatch but cannot recall an already-dispatched message. Duplicate or concurrent approval claims cannot authorize a second send.

## Evidence

`tests/test_disclosure.py` has 16 free tests: exact rendered review and delivery, missing-line rejection, capability selection, denial/concurrent approval, changed sources/restrictions, manual-route bypass, target-key deduplication, uncertain readback, later-process review, stop/reissue, irreversible rollback and an independent negative control for undisclosed outgoing text. `tasks/dev/disclosed_send.yaml` exercises the shared runner/service/approval path with `checks/disclosed_send.py`. Existing course task checks independently inspect all agent-authored outgoing messages through `agent_disclosures_valid`; draft-only tasks still require zero agent sends.

The [rendered approval example](evidence/SEND_APPROVAL.html) and [computed screen data](evidence/SEND_APPROVAL.json) are a synthetic local example generated without model API calls. They demonstrate screen content, not real-human reading time or approval quality. Whole-plan review, attention measurements and full remaining-task continuation are still open in [the checklist](PART2_CHECKLIST.md).
