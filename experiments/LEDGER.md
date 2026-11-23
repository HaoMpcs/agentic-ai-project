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
- **Results:** pass1-plan-on passed 0/3, used 12,851 tokens, cost $0.014348, had five plan rejections, and ended twice at plan_rejected and once at plan_fill_error. pass1-plan-off passed 3/3, used 44,305 tokens, cost $0.016759, and had zero plan rejections and zero false finishes.
- **Difference:** Off minus on: +3 passing runs, +31,454 tokens, +$0.002411 total cost, and -5 plan rejections. Median turn increased from 1.909 to 2.514 seconds (+0.605 seconds).
- **Verdict:** Keep `plan.batch=off`. The loop completed every batch; the plan completed none.
- **Links:** results/pass1-plan-on/ and results/pass1-plan-off/.

## Pass 2 · Reduce the full tool-definition bill

- **Pass:** 2; compare full tool loading with deferred catalogue loading.
- **Owner:** Part 3/integration owner; name pending team confirmation.
- **Problem:** The real M2 build passed 33/33, so there is no correctness failure to repair. Its nine Agent-path runs consumed all 107,257 model tokens. Every model call offered the full default tool surface; the three batch runs used 14,906, 15,264 and 15,264 tokens.
- **Evidence:** `m2-build-batch_questions-s01-2b4b19`, `s02-05a411` and `s03-6a1129`; the build summary records 104,217 input and 3,040 output tokens, $0.038866, and no failed runs.
- **Why this fix:** Lecture 3's definition-bill test asks whether repeatedly transmitting tools the model does not need consumes a material window share. Deferred loading is already built behind a switch and preserves Registry/policy checks; this pass measures whether its smaller initial surface offsets catalogue-search calls.
- **Prediction:** `m2-pass2-tools-deferred` will pass at least 8/9 and use at least 10% fewer total input tokens than `m2-pass2-tools-all`. It may use more model/tool calls, but will have zero catalogue misses for a tool eventually required. `m2-pass2-tools-all` will pass at least 8/9.
- **Arms:** `results/m2-pass2-tools-all` with `tools.loading=all`; `results/m2-pass2-tools-deferred` with `tools.loading=deferred`. Both explicitly keep `topology=single`, `plan.batch=off`, and `code_calls.batch=off`.
- **Held constant:** Same committed code, Gemini 3.5 Flash-Lite, settings and price sheet, 32,000-token task bound, checks, task inputs, three sweeps, sequential jobs, all other switches and scripted operator behavior.
- **Tasks and sweeps:** `tasks/ambiguous_question.yaml`, `tasks/batch_questions.yaml`, and `tasks/conceptual_question.yaml`; three sweeps per arm, nine runs each.
- **Results:** Both arms passed 9/9. All used 107,283 input + 3,084 output = 110,367 tokens, $0.039895, 57 model calls and 115 tool calls. Deferred used 155,408 input + 3,589 output = 158,997 tokens, $0.055595, 74 model calls and 132 tool calls, including 22 catalogue calls. Median turn was 1.8695s all and 2.257s deferred.
- **Difference:** Deferred minus all: +48,125 input tokens (+44.9%), +48,630 total tokens, +$0.015700, +17 model calls, +17 tool calls and +0.3875s median turn, with no pass-rate change. The predicted 10% input reduction was wrong; catalogue turns outweighed the smaller initial surface.
- **Verdict:** Drop deferred for this workload and keep `tools.loading=all`. Seven default model-facing tools are below the point where search pays for itself; retain the alternative and reopen only after the surface or per-call definition share grows materially.
- **Links:** `results/m2-pass2-tools-all/` and `results/m2-pass2-tools-deferred/`.

## Pass 3 · Keep batch intermediates out of model context

- **Pass:** 3; compare the bounded agent loop with restricted code calls for the batch use case.
- **Owner:** Part 3/integration owner; name pending team confirmation.
- **Problem:** Pass 2 showed that adding catalogue model turns increased input by 44.9%. With full loading retained, `batch_questions` remains the largest Agent task: its three Pass 2 control runs used 15,265, 15,376 and 15,330 total tokens. Repeated model round trips carry tool definitions and intermediate results.
- **Evidence:** `m2-pass2-tools-all-batch_questions-s01-ba3497`, `s02-1f6ed7`, and `s03-eb1b3f`; all passed, so the pass targets input/model-call cost without relaxing the independent sandbox check.
- **Why this fix:** Lecture 3's code-call test applies to a bounded loop over several records. The implemented restricted program can call only the Registry, uses no imports/files/network/attributes, retains the task's shared bounds and keys, and returns only a small final result to the next model call.
- **Prediction:** `m2-pass3-code-on` will pass at least 2/3 and use at least 20% fewer total input tokens than `m2-pass3-code-off`. `m2-pass3-code-off` will pass at least 2/3. Every on-arm domain call will still appear as a Registry/MCP tool call, and no intermediate tool result will enter the model context.
- **Arms:** `results/m2-pass3-code-off` with `code_calls.batch=off`; `results/m2-pass3-code-on` with `code_calls.batch=on`. Both explicitly keep `tools.loading=all`, `topology=single`, and `plan.batch=off`.
- **Held constant:** Same committed code, Gemini 3.5 Flash-Lite, settings and price sheet, 32,000-token task bound, batch fixture/check, three sweeps, sequential jobs, all other switches and scripted operator behavior.
- **Tasks and sweeps:** `tasks/batch_questions.yaml`, three sweeps per arm.
- **Results:** Pending; run only after this prediction commit is pushed.
- **Difference:** Pending.
- **Verdict:** Pending; retain `code_calls.batch=off` until both arms are recorded.
- **Links:** Pending `results/m2-pass3-code-off/` and `results/m2-pass3-code-on/`.
