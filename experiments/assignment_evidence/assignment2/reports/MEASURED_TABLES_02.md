# Automatically derived Assignment 2 tables

Source: finished, non-scripted traces under runs/ and run-id-matched tracker comments.

| Metric | Agent | Planned off | Planned self | Planned external |
|---|---:|---:|---:|---:|
| runs | 18 | 18 | 18 | 18 |
| passes | 11 | 7 | 3 | 6 |
| per_issue | {'4201': 3, '4202': 1, '4203': 3, '4204': 1, '4205': 3, '4206': 0} | {'4201': 3, '4202': 0, '4203': 3, '4204': 0, '4205': 1, '4206': 0} | {'4201': 3, '4202': 0, '4203': 0, '4204': 0, '4205': 0, '4206': 0} | {'4201': 3, '4202': 0, '4203': 2, '4204': 0, '4205': 1, '4206': 0} |
| sweep_min | 3 | 2 | 1 | 2 |
| sweep_max | 4 | 3 | 1 | 2 |
| mean_tokens | 1.277e+04 | 4415 | 3729 | 4408 |
| p50_latency_s | 4.488 | 5.18 | 4.415 | 4.366 |
| max_latency_s | 9.056 | 7.786 | 7.568 | 6.711 |
| plan_overhead_share | — | 0.5413 | 0.6555 | 0.5297 |
| critique_overhead_share | — | — | 0.04744 | 0.0173 |
| runs_with_repeat | 3 | 1 | 0 | 0 |
| off_plan | — | 0 | 0 | 0 |
| revisions_mean | — | 1.222 | 1.167 | 1 |
| revisions_max | — | 2 | 2 | 2 |
| rounds_mean | — | — | 0.1667 | 0.5 |
| rounds_max | — | — | 1 | 2 |
| drafts_changed | — | — | 0 | 1 |
| drafts_fixed | — | — | 0 | 0 |
| drafts_broken | — | — | 0 | 0 |
| drafts_held | — | — | 0 | 1 |

## Part G

| Run ID | Issue | Notes shown | Compacted | Correct / 6 |
|---|---:|---|---|---:|
| notes-4203-s01-09835b | 4203 | False | True | 5/6 |
| notes-4203-s01-9c6b10 | 4203 | True | True | 6/6 |
| notes-4203-s02-136c47 | 4203 | False | True | 6/6 |
| notes-4203-s02-cf44f4 | 4203 | True | True | 6/6 |
| notes-4204-s01-3dacc1 | 4204 | True | True | 6/6 |
| notes-4204-s01-e1c656 | 4204 | False | True | 6/6 |
| notes-4204-s02-a32716 | 4204 | False | True | 6/6 |
| notes-4204-s02-f23b99 | 4204 | True | True | 3/6 |
| notes-4206-s01-b30166 | 4206 | True | True | 6/6 |
| notes-4206-s01-b8d1f5 | 4206 | False | True | 3/6 |
| notes-4206-s02-151f10 | 4206 | True | True | 6/6 |
| notes-4206-s02-25baa6 | 4206 | False | True | 6/6 |

## Planning overhead by model-call count

| Configuration | Model calls in run | Mean share of prompt tokens for plan/revise |
|---|---:|---:|
| planned_off | 3 | 0.7933 |
| planned_off | 4 | 0.2693 |
| planned_off | 5 | 0.7354 |
| planned_off | 6 | 0.5028 |
| planned_self | 3 | 0.7924 |
| planned_self | 5 | 0.4967 |
| planned_self | 6 | 0.5952 |
| planned_external | 3 | 0.7941 |
| planned_external | 4 | 0.2704 |
| planned_external | 6 | 0.4252 |
| planned_external | 7 | 0.1888 |

## Planning tokens compared with execution, per issue

| Configuration | Issue | Plan + revise prompt tokens, mean | Executor prompt tokens, mean | Planner costlier? |
|---|---:|---:|---:|---|
| planned_off | 4201 | 787.0 | 2135.7 | False |
| planned_off | 4202 | 2276.7 | 1380.0 | True |
| planned_off | 4203 | 1657.7 | 3282.7 | False |
| planned_off | 4204 | 2530.0 | 1343.3 | True |
| planned_off | 4205 | 1665.7 | 1773.3 | False |
| planned_off | 4206 | 2238.7 | 962.0 | True |
| planned_self | 4201 | 787.0 | 2133.3 | False |
| planned_self | 4202 | 1974.3 | 656.7 | True |
| planned_self | 4203 | 1663.0 | 451.0 | True |
| planned_self | 4204 | 2233.3 | 877.7 | True |
| planned_self | 4205 | 1964.0 | 1018.3 | True |
| planned_self | 4206 | 2249.3 | 780.7 | True |
| planned_external | 4201 | 787.0 | 2123.3 | False |
| planned_external | 4202 | 1970.7 | 965.3 | True |
| planned_external | 4203 | 1649.3 | 2329.3 | False |
| planned_external | 4204 | 1644.0 | 1352.0 | True |
| planned_external | 4205 | 1998.3 | 2547.0 | False |
| planned_external | 4206 | 1936.7 | 2178.7 | False |

## Notes token cost (mean across runs)

| Notes shown | Runs | Mean all tokens | Mean context questions correct / 6 |
|---|---:|---:|---:|
| False | 6 | 5195 | 5.333 |
| True | 6 | 5936 | 5.5 |

Schema failures in measured planned runs: 25 schema events across 54 planner calls (plus any revision rejections).
