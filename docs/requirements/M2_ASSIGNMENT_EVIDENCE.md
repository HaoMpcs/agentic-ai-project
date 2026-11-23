# Milestone 2 assignment evidence

Read locally on November 22, 2026. These are historical assignment measurements,
not Course Q&A Assistant experiment arms. No assignment runtime code was imported.

## Assignment 2 — notes and compaction

Jingyu Huang's retained Assignment 2 report is at
`experiments/assignment_evidence/assignment2/reports/LAB_02.md`. It records 12
real Gemini context runs, all compacted at an approximately 350-token threshold.
Notes off answered 32/36 context questions (88.9%) at 5,195 mean tokens; notes
on answered 33/36 (91.7%) at 5,936. The +2.8 percentage-point result cost about
14.3% more tokens and was inconsistent: one issue/replicate fell from 6/6 to
3/6 with notes. This predicts at most a small, uncertain benefit for our safe
notes and supports retaining environment checks rather than trusting summaries.

## Assignment 4 — restart, keys and boundaries

Jingyu Huang's retained report is
`experiments/assignment_evidence/assignment4_runtime/LAB_04.md`. With stable
derived keys, all ten crash positions recovered with exactly one comment and
one pull request. Replacing them with UUID keys duplicated comments in both
step-5 commit-before-acknowledgement cases. Five structured checkpoints used
28,933 bytes; copies including conversation used 134,981 bytes, a 4.67x
multiplier. Its boundary experiments separately observed an attention failure,
a fact lost at compaction and repaired by a structured note, and a fact lost
between sessions and repaired by provenance memory. These figures motivate our
same-key three-exit recovery and separation of checkpoint, notes and memory.

## Assignment 5 — reviewer attention

Hao Shi's local Assignment 5 repository was read at commit
`80557f9f99e556bd3fb840c6a067a9094e101491` (Git author `HaoMpcs
<haocs@uchicago.edu>`). The source report was
`/Users/tofu/Desktop/AgentAI/hw5/AgenticAI-HW5/reports/LAB_05.md`, SHA-256
`f75677374b8f660acb33fc8e4dce857f010ee21799ef10931d3e2e46925e204f`.
Its replay estimated 15 prompts/day and 40 seconds/prompt from a ten-minute
daily budget. It reports 17 human decisions: 15 `open_pr` at 16.0-second median and two
`post_comment/human_active` at 18.8 seconds, all approved. The day contained no
planted bad request, so 100% approval does not establish detection quality. Its
fixed-plan review reduced the replay estimate from 15 to 12 prompts, excluding
revision re-reviews. Ten live stops had 3.081-second median and 4.771-second
maximum response; all resumed without duplicate writes. For this project these
are workload priors, not measurements of our screens. Our scripted approvals
must not be reported as human reading time.

## Assignment 6 — split multiplier and matched spend

Hao Shi's local Assignment 6 repository was read at commit
`8c2a5d1a9c1fbb661e57eaa3905f86bba0a784cd`; source
`/Users/tofu/Desktop/AgentAI/hw6/AgenticAI-HW6/reports/LAB_06.md`, SHA-256
`650c44c8b27dc68a9b546a7bf83e122355612e48cdcd7098b8474d5d2ab95cb0`.
The measured split/single token multiplier was 0.49x for single issues and 0.40x
for batches. At matched actual spend, sequential S-plus matched split M at
12/18 single-issue passes and exceeded it on all-three-sweeps tasks (four versus
three). On batches, both M and S-plus passed 0/6; M was faster, 22.6 versus 37.4
seconds. The assignment therefore kept one agent for both task kinds. This
predicts that lower spend or focused contexts alone cannot establish a topology
benefit and supports our decision to retain, but not merge, `m2-split`.

AI assistance: Codex located the existing reports, extracted the requirement-
relevant figures and recorded provenance. Team members must verify the owner
attribution and figures before submission.
