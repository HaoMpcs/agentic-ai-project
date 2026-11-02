# Real-model evaluation protocol

The retained baseline contains 30 real-model runs (27 passed). Pass 1 is complete:
results/pass1-plan-on and results/pass1-plan-off contain three batch runs each,
with 0/3 and 3/3 passing respectively. The advance prediction is in commit
1fb5ea4 and the verdict keeps plan.batch=off. See LEDGER.md and M1 Part 4.
Free smoke records remain separate and cannot support model cost/quality claims.
The procedure below applies to new measurements; preserve the existing arms.

1. Review the supplied milestone criteria and the retained Assignment 1-3
   evidence in docs/requirements/ASSIGNMENT_EVIDENCE.md. Confirm the current
   domain's gate estimates, representative Agent cases and experiment owner.
2. Select provider/model/key in the documented settings interface; verify the
   provider's current price and strict-mode documentation. Record source/date.
3. Run `make ping`, tests and checks; commit engineering code. Official arms
   must not run on dirty code.
4. Run `python run.py --tasks tasks/ --sweeps 3 --arm baseline` (10 tasks,
   30 runs), then analyze records and every failure trace. Cite the earliest
   cause by run ID and one-based trace line. Review plan repeats/orphans,
   completeness and task fit first. Investigate turns above ten seconds.
5. Choose exactly one evidence-supported intervention. If justified failures
   are absent, follow the official rule for at most three harder tasks and a
   new baseline; do not silently expand the held-out set.
6. Complete Pass 1 in LEDGER with numeric prediction, baseline evidence, one
   switch, owner, constants, task set and three sweeps. Commit the prediction,
   then obtain authorization and push it. Do not start the arms until the push
   is verified. Preserve the prediction after measurement begins.
7. Run fresh `pass1-off` and `pass1-on` arms on identical committed code/model/
   settings/tasks and three sweeps, changing only the selected switch. Do not
   reuse baseline as the off arm.
8. Recompute with `python -m experiments.analysis.summarize results/pass1-off
   results/pass1-on`. Compare success, costs, tokens, latency and the chosen
   intervention's trace metrics. Record a keep/drop verdict, including negative
   outcomes. Tool overhead is a separate real-API measurement.

The analysis command refuses free records unless `--include-free` is explicitly
supplied. It checks one configuration per arm, reports per-task/per-sweep counts,
median and worst turn, slow runs, token and monetary totals, distinct tool
sequences, repeats, errors, critique rounds/holds, plan rejections/revisions,
execution/skipped/extra/out-of-order steps, and exact first-problem trace lines.
Provider calls still in flight mark billing incomplete and monetary totals
unknown. Genuine incomplete or unpriced data must be reconciled before claiming
an economic result.
