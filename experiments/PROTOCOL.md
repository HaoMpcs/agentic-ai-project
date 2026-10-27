# Real-model evaluation protocol — pending

No real-model baseline or improvement arm exists. Thirty retained free smoke runs
exercise mechanics and cannot support a milestone cost or quality claim.

1. Obtain the official spec and actual Assignment 1–3 evidence. Confirm owner.
2. Select provider/model/key in the documented settings interface; verify the
   provider's current price and strict-mode documentation. Record source/date.
3. Run `make ping`, tests and checks; commit engineering code. Official arms
   must not run on dirty code. No remote operation has been authorized.
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
