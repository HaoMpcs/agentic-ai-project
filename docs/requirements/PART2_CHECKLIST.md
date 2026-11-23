# Part 2 final checklist

Owner: Yani Wu. Reconciled November 22, 2026 after integration. The earlier
increment statuses are preserved in `M2_COMPLIANCE.md` as historical evidence;
this file records current submission status.

## Tasks 1–9

| Task | Current status | Final evidence or remaining work |
|---|---|---|
| 1. Rank every action | Complete | `PART2_POLICY.md`, `policy/autonomy.yaml`, and the M2 Part 2 ranking table cover reads, internal writes, sends and prohibited circumstances |
| 2. Three-column policy | Complete | Independent, requires-approval and prohibited classes use the same identifiers in policy and traces |
| 3. Hook and operator limits | Complete | Stop-first, fail-closed Registry hook; persisted code-parsed limits; outside text has no authority |
| 4. Approval gate and queue | Complete | Durable per-action and fixed-plan review, exact saved calls, revision/unlisted-action re-gating, computed page and Queue lifecycle tests pass; six human decisions and both screen classes are retained |
| 5. Escalation | Complete | Named unknown-write signal, three-field packet, checkpointed hold, 24-hour deadline, shared 20/day cap and later-session resolution |
| 6. Stop/cancel/resume/rollback | Complete with stated limitation | Five-condition evidence, three commands, approval withdrawal/reissue and reverse compensation. An already-dispatched call cannot be forcibly preempted and is recorded |
| 7. Mid-task messages | Complete | Add/replace/eight-slot FIFO/reject paths, persistence and concurrent tests |
| 8. Disclosure and legal scope | Complete for this system | Code-added AI identity/contact, missing-line refusal, exact-send review and dated scope analysis |
| 9. Reviewer attention | Human sample complete; framework labels pending | Inventory, shortcuts, cap/placement choices, Assignment 5 evidence and project human asks/rates/times are in M2.md. Confirm exact named course-framework levels before final tag |

## Final submission checklist

- [x] Cite Assignment 5: 15 prompts/day, 40 seconds/prompt, 15-to-12
  plan estimate, class medians/approval rate, and ten-stop latency.
- [x] Include action ranking, autonomy classes, approval choices and escalation
  signal in the M2 report.
- [x] Include an appendix inventory for each gated action class, with every line
  labelled computed, asserted, or outside/untrusted.
- [x] Include Yani Wu's ownership and the team AI-assistance disclosure.
- [x] Add real-human decisions by action class, asks/run, the declared real day,
  reviewer minutes, asks/day, seconds/ask, rates and median times.
- [x] Add clean synthetic approval-page captures from that human run.
- [x] Confirm the exact Knight Institute and Interface/Ada Lovelace level names
  from the course slides; CSA Tier 2 obligations are already described.
- [x] Create and push the final `m2` tag after the preceding items and final
  clean-checkout verification.

Scripted decisions remain mechanism evidence and are never reported as human
reading time. The final report is authoritative if an older incremental document
describes work as pending.
