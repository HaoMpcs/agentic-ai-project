# The ledger

One entry per pass: copy the template to the end of this file, under `## Pass N · <the
problem, in a few words>`. The Project page says what each field holds and when to commit
it. `make check` reads every `##` section but the template: see the README's "make check".

## Template

- **Pass:** <its number, the problem, the fix>
- **Owner:** <a member>
- **Problem:** <the symptom>
- **Evidence:** <run IDs and trace lines>
- **Why this fix:** <your reason>
- **Prediction:** <per arm, with a number>
- **Arms:** <each arm's folder and switches>
- **Held constant:** <what did not change>
- **Tasks and sweeps:** <test tasks, sweeps per arm>
- **Results:** <per arm, with counts>
- **Difference:** <after minus before>
- **Verdict:** <keep or drop, and the switch's setting>
- **Links:** <results/<arm>/ for every arm>

## Pass 1 · Remove the failing batch plan

- **Pass:** 1; turn the batch plan off.
- **Owner:** Hao Shi.
- **Problem:** The real baseline passed 27/30 runs, but batch_questions passed 0/3. Every batch failed in planning or runtime placeholder filling before a reply was written.
- **Evidence:** baseline-batch_questions-s01-63f59a trace line 8; baseline-batch_questions-s02-73602d trace lines 8 and 47; baseline-batch_questions-s03-d48388 trace line 8.
- **Why this fix:** Lecture 2 says a plan does not help when it adds more failure cost than the validator or diff catches. The bounded loop can investigate and repair one call at a time.
- **Prediction:** pass1-plan-off will pass at least 2/3 runs with 0 plan rejections; pass1-plan-on will pass at most 1/3 with at least 2 plan rejections.
- **Arms:** results/pass1-plan-off with plan.batch=off; results/pass1-plan-on with plan.batch=on. All other switches stay at their recorded defaults.
- **Held constant:** Gemini 3.5 Flash-Lite, settings, committed code, batch task, other switches, price sheet and check.
- **Tasks and sweeps:** tasks/batch_questions.yaml, three sweeps per arm, after this prediction is committed and pushed.
- **Results:** pending
- **Difference:** pending
- **Verdict:** pending
- **Links:** pending
