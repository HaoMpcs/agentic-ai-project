# Part 2 task checklist

Owner: Yani Wu. Checked November 22, 2026 (America/New_York) against the saved [M2 requirements](M2_REQUIREMENTS.txt) and current source. Part 2 is **not complete**. Implemented control foundations must not be confused with completed task continuation or final report evidence.

## Assignment tasks 1–9

| Task | Status | Implemented / evidence | Still required |
|---|---|---|---|
| 1. Rank every action before gating | Done for current capabilities | PART2_POLICY.md ranks existing reads/drafts/flags and prohibited circumstances; PART2_STOP.md explains owned compensation | Automated send classes are ranked in PART2_DISCLOSURE.md; rank plan-review circumstances before exposing them |
| 2. Three-column policy | Done for current capabilities | policy/autonomy.yaml has independent/requires_approval/prohibited classes; circumstances include explicit operator restrictions | Automated sends now require approval; restricted internal drafts remain a distinct action class |
| 3. Registry hook and operator limits | Done for supported commands | policy/hook.py; code-parsed persisted /limit rules, stop first, no prohibition override, failure denies; tests/test_autonomy.py | New roles/transports must use the same hook. Arbitrary natural-language restrictions are not all parsed; supported forms are documented |
| 4. Approval gate, plan/action choice and queue | Partial | Immutable per-action draft/flag requests, computed HTTP screen, same callbacks for app/runner, restart, exact call/key execution; queue covers pending/uncertain/escalated/stopped work | Whole-plan mode; dated approval.<use_case> switch; both use-case decisions; unlisted/revised actions re-gated; actual rendered screen for remaining gated classes in appendix; full remaining-task continuation |
| 5. Escalation | Partial, control layer works | Named unknown-write signal, three-field packet, saved hold, deadline, shared daily cap, over-cap queue, later-process confirmation of matching existing effect | Integrate full Part 1 checkpoint and absent-effect same-key recovery; after an operator answer, continue remaining steps with saved budget; finish covered/not-covered use-case decisions |
| 6. Stop, cancel/resume/rollback | Partial, control layer works | Immediate command; durable flag/call snapshot; gate withdrawal/reissue; permanent cancel; reverse owned compensation; five probes with latency evidence | Full checkpoint/model/plan continuation, stable app run numbers and real outside-wait end-to-end tests depend on Part 1. Already-dispatched work cannot be preempted; retain this limitation |
| 7. Operator messages mid-task | Implemented for live workflows/agents and gate replacement; integration partial | policy/messages.py; 17 concurrent/persistence tests; fixed_run/check_run fixtures and checks/midtask.py; add/replace/FIFO queue/reject, limits, fresh run keys and selected compensation | Complete restarted/outside-wait continuation through Part 1; do not claim persisted inbox alone resumes a task |
| 8. Agent disclosure and legal applicability | Implemented for current local capabilities | PART2_DISCLOSURE.md; code-added identity/contact paragraph; exact final-body gate; missing-line denial; manual bypass blocked; independent outgoing checks; rendered send appendix; PART2_LEGAL.md with dated EU/Colorado/California primary sources | Reassess jurisdiction and intended purpose before real deployment; external transport and full recovery remain Part 1 integration work |
| 9. Reviewer attention inventory/frameworks | Not completed | Gate decisions have actor/class/time fields; stop probes are free tests | Actual asks/run with n and approval mode, declared day/reviewer minutes, asks/day and seconds/ask; real-human class rates/times, screen-shortcut analysis, attention decisions; three framework placements and obligations |

## Citation and write-up checklist

- [ ] Cite the named Assignment 5 repository and verified numbers: prompts/day, seconds/prompt, plan-review savings, class-specific approval rate/median reading time and stop latency/sample count.
- [ ] Complete Part 2 decision-table rows for each action circumstance, plan/action use case and escalation signal, with yes/no cases and evidence.
- [ ] Add actual approval-screen examples per gated class, labelled computed/asserted; a field inventory alone is not the required rendered appendix.
- [ ] Complete legal and framework sections with dated primary sources. This checklist does not assert legal conclusions.
- [ ] Separate scripted decision times from real human reading measurements.
- [ ] Include Yani Wu's ownership and AI-assistance disclosure in the final report.

Local A5 source exists at ../a5_57220_yaniw/reports/LAB_05.md and LAB_05.json. The Markdown report currently contains empty Part B human-approval tables and an empty Part C stop-results table. It does report the Part A replay estimate of 14 prompts/day and 42.86 seconds/prompt from a ten-minute budget. That estimate is not human reading time. Inspect retained raw A5 evidence before deciding which missing numbers can be reconstructed; do not invent them or substitute current free stop probes for historical A5 measurements.

## Boundary with Part 1

Part 2 owns policy, approval/hold/stop records, operator controls and outgoing disclosure. Part 1 must supply durable app run identity, the full task checkpoint/journal, saved remaining budget, outside-wait state and continuation entry. Current action snapshots and single reviewed-call replay do not establish that entire tasks resume. Integration tests must cover approve/stop/reply after restart, a silent operator, preserved completed effects and no duplicate writes.

## Next work in order

1. Fixed-plan approval, per-action alternative, dated switches and revision/unlisted-action tests (task 4).
2. A5 attribution, remaining rendered screen appendix, real-human review evidence and framework write-up (tasks 4 and 9).
3. Joint Part 1 integration and final restart/wait/continuation acceptance tests (tasks 4–7).

Latest verified suite: 189 tests passed, including 87 tests across autonomy (12), approvals (15), escalation (14), controls (13), messages (17) and disclosure (16); make check passed all four checks with 14 task files. The message implementation and fixtures are tested; no formal measured improvement results are added. Details: [PART2_MESSAGES.md](PART2_MESSAGES.md) and [PART2_DISCLOSURE.md](PART2_DISCLOSURE.md). Work remains uncommitted and unpushed.
