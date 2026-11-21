# Milestone 2 Part A verification

Owner: **Jingyu Huang (CNetID: jyhuang28)**. Date: **November 21, 2026,
America/Chicago**. Branch: `codex/m2-runtime`, based on main commit `216f0b6`.
The report verifies working-tree source fingerprints, not a pushed submission tag.

Scope: durable execution state, recovery, unknown writes, MCP, deferred loading,
restricted code calls, the outside wait, compensation, and B/C integration
adapters. It does not certify Parts B/C, the topology branch, or the M2 baseline
and two improvement passes. All model-dependent verification uses free fakes.

## Results

| Check | Actual result | Original evidence |
|---|---|---|
| Full project suite | **127/127 passed**, zero failures/errors | [make-test.log](../../experiments/reports/m2-part-a-20261121/make-test.log) |
| Part A tests | **25 test methods**, included in the passing full suite | tests/test_m2_runtime.py; source hashes in summary.json |
| Structural checks | All **4 passed**; 13 tasks, 15 switches, existing ledger accepted | [make-check.log](../../experiments/reports/m2-part-a-20261121/make-check.log) |
| Kill after the final write on every task, including dev tasks | **13/13 cases recovered** under the same run identity | [recovery snapshots/traces](../../experiments/reports/m2-part-a-20261121/recovery/) |
| Effects across that recovery matrix | **17 after crash, 17 after resume; 0 duplicates** | Each snapshot contains SQL effect rows before, after crash and after resume |
| Repeated completed execution calls after resume | **0 across 13 cases** | MCP events after each recorded crash boundary, filtered to that run key |
| Planned and code-call recovery | Saved plan/program restored; one effect per question | Dedicated process-kill tests |
| Real SDK calls | MCP SDK 1.30.0; fixed order twice; execution and protocol errors distinct | [mcp-contract.json](../../experiments/reports/m2-part-a-20261121/mcp-contract.json) |
| Local app restart | Actual `make app`, stop, then `make serve`; original session and wait retained | [app-smoke.json](../../experiments/reports/m2-part-a-20261121/app-smoke.json), log and app-session.jsonl |
| Recomputed metrics | Retained snapshots/traces reproduce metrics exactly | [metrics.json](../../experiments/reports/m2-part-a-20261121/metrics.json) |
| Source integrity | Original Assignment 4 report hashes verified; current source fingerprints retained | [summary.json](../../experiments/reports/m2-part-a-20261121/summary.json) |

## What the tests establish

The crash test starts each task in a fresh process with `fixed_run`, then sends
SIGKILL after the final sandbox write commits but before its call result is
journaled. A new process opens the same run ID with `fresh=False`, resumes through
the service entry point, and runs `check_run`. All 13 task files are included.
Assertions use sandbox rows and channel messages; no success claim is trusted.
Expected negative-control task checks are not failed unit tests.

The matrix retains the pre-run effect state (empty after seed), committed effects
after the crash, and effects after resume. `crash_trace_lines` fixes the boundary
in each copied trace. The analysis counts actual MCP requests following it, not
the agent's description of what it repeated. Journal reuse is recorded separately.
The independent task checks also return `duplicate_effects` from sandbox rows.

Separate cases test a crash in the non-atomic channel/outbox gap, asking and
answering in different processes, duplicate outside replies, an invalid reply
claiming operator authority, and the seeded deadline. Unknown writes exercise
all exits: confirmed writes reuse the existing result, absent writes retry under
the same key, and an unreadable result holds for staff without another effect.
Compensations are keyed, applied in reverse order and retain audit history.

Deferred loading tests check the small initial tool set, definitions added on
the next request, and logged empty search results. The restricted program tests
exercise real Registry/MCP calls, keyed writes and hook rejection. Imports,
network/file access, attributes, unsupported control flow and oversized values
return repairable errors. Intermediate tool results stay out of model context.
This is a capability interpreter, not unrestricted Python with a cosmetic filter.

Adapter tests establish that C's control callback runs before B's context
assembler, cumulative bounds survive resume, replay checks saved arguments,
and stale stop/progress updates cannot overwrite each other. A cross-console
resume keeps the original session's effect stamp. These tests do not replace
the actual policy, approval, stop UI, notes or memory implementation.

## Local HTTP observation

The smoke uses temporary state, results and traces, a free backend and a local
loopback server. A console request for `SYN-Q-clarify` sends one fixed disclosed
question and waits. After stopping the server, `make serve` preserves both the
session listing and the wait. Posting `deadline` from Threads creates exactly
one pending grounded reply stamped with the original console session. The
follow-up reads that effect. Servers are stopped after the observation; no
real model or external system is contacted.

## Sources, limits and integration

Assignment 4's retained original report describes **10 stable-key crash cases**
with one comment each and **2 duplicate cases among 10 broken-key cases**. The
analyzer verifies the report files and reproduces these reported matrix counts;
it does not claim independent tracker regrading or treat those as project runs.
No assignment runtime code was imported.

MCP 1.30.0 declares protocol 2025-11-25. Each request uses a fresh SDK server over
memory streams with no initialize exchange or retained server state. The artifact
records this compatibility adapter, not native implementation of the newer
revision. The default model surface has seven domain tools; the server has
eleven including code/operator-only functions and catalogue search. Zero strict
tools are selected, so no vendor strict-acceptance measurement is claimed.

The build is a recovery aid: it has checkpoints, a journal and keyed writes,
but no automatic crash supervisor. Provider billing unknown at a killed or timed
out model call is not converted into a known cost. No real-model accuracy,
latency, savings or formal improvement verdict is asserted by this report.

B must implement its context/memory adapter and complete long/later-session
tests; C must implement policy, approvals, escalation, stop/messages and its
disclosure enforcement. The team then runs the complete M2 baseline and two
sequential passes with advance-pushed predictions. See the
[handoff contracts](M2_PART_A_HANDOFF.md) and [M2 record](../milestones/M2.md).

## Reproduce

```bash
make setup
.venv/bin/python -m unittest tests.test_m2_runtime -v
make test
make check
.venv/bin/python -m experiments.analysis.m2_runtime experiments/reports/m2-part-a-20261121/recovery
```

Use a fresh output folder with `PART_A_EVIDENCE_DIR=<folder>/recovery make test`
to capture another recovery bundle. Existing measured experiment arms and
predictions are untouched. All report and source hashes refer to the retained
working-tree verification; final clean-clone/tag verification remains a team task.

AI assistance: Codex wrote Part A and this report; verification used the full
suite, actual SDK dispatch, process-kill/new-process tests, local HTTP restart,
sandbox reads, source hashes and independent metric recomputation.
