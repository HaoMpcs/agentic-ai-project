# Tool and action contracts

The authoritative executable schemas are `agent/tools.py:SCHEMAS` and
`RESULT_SCHEMAS`. Every argument object is closed and every declared parameter
is required. Strings have explicit length bounds; arrays and enum values are
validated in code as well as the starter schema checker. IDs refer to seeded
SYN- records, never file paths. Tool results have a named container, not opaque
text. All tools use the same registry, including workflows and planned steps.

| Tool | Arguments | Successful result and empty meaning | Max UTF-8 bytes | Caller / credential scope | Failure/repair |
|---|---|---|---:|---|---|
| course_get_question | question_id: string <=120 | question: ID, staff kind/topic, untrusted_messages (last 3, each <=4000 chars) | 14,000 | Agent/workflow/executor; selected question IDs only | Unknown/out-of-scope ID; select inbox ID |
| course_search_materials | query: string <=160 | documents: <=6 active public summaries, exact topic preferred; [] means no source | 4,000 | Agent/workflow/executor; public course index | Oversized/empty query; narrow it |
| course_read_document | document_id: string <=120 | document: facts, joined answer, comparable claims, active/version/topic | 6,000 | Agent/workflow/executor; active public documents only | Missing/inactive/private ID; search for current ID |
| course_search_public_answers | topic: string <=120 | answers: <=4 public answers and source IDs; [] means none | 6,000 | Agent/workflow/executor; public history only | Repair topic; prior answer is not current authority |
| course_create_reply | question_id, body <=2500 chars, source_ids <=6 strings | effect: persisted first action result, ID, pending status and stamp | 4,000 | Agent/workflow/executor; selected read question + already read public sources | Repair citation/support error; privacy refusal fixed; personal requests forbidden |
| course_create_flag | question_id, reason enum | effect: first action result, ID/open status/stamp | 4,000 | Agent/workflow/executor; selected read question, reason-only flag | Enum: private_request, staff_decision, missing_information, conflicting_sources |
| course_status | question_id | effects: first <=12 effects for selected question; [] means no recorded work | 48,000 | Agent/workflow/executor; selected questions | Repair question ID |
| course_list_flags | status enum: open/cleared/all | flags: <=30 records; [] means no matching flags | 32,000 | Trusted operator summary only; absent from model definitions | Denied for agent/workflow/executor; correct caller or scope |

Flags contain a categorical reason rather than student text. Agent credentials
are local sandbox capabilities, not model-supplied credentials. Private student
records cannot be reached through any tool. Console selection, routing metadata,
and the summary's environment reads are code-controlled. The application is a
local trusted-operator demo with synthetic data; it has no production user-auth
system.

Every attempted registry call traces its complete original input, bounded
result, error class, latency, attempts, cost (zero for these local operations),
action key, caller and step/plan-step identifiers. Unknown tool names get a short
generic error, not a traceback. Content validation runs on results even when
provider strict mode is off. Pre-call hook exceptions deny the call. A failed
result contract is an internal error, never evidence of success.

Transient connection/busy failures retry at most three attempts with 10 ms and
20 ms backoff, with the same key. Permanent schema, missing-record or permission
errors return concise repair facts. Timeout after a write is ambiguous: no
registry retry; the agent halts and staff inspect status. This is not full M2
recovery. Public model backends retain the starter retry policy; the independent
45-second application deadline stops further tool dispatch even if an SDK is
still waiting. Late provider billing cannot be considered a complete measure.

Keys are `sha256(JSON([run_id or session_id or manual, tool_name, question_id]))`.
The model never chooses them. Generated body, tool-call ID and plan version do
not enter identity. The first persisted action wins, including a reworded retry.
A revised plan references the same logical question action, so its new version
cannot create a duplicate. Different action types have distinct keys; the
independent check rejects a run leaving both a reply and a flag for one case.

Manual drafts and flags use explicit `manual:` keys and `manual` stamps. Manual
send claims `pending -> sending` with a conditional SQLite update before calling
`channel.send(..., sender="operator")`. Duplicate HTTP posts after `sent` return
the existing result. There is a cross-database boundary: a crash after the claim
or channel insert can leave `sending`/`uncertain`. No automatic retry is allowed;
staff inspect Threads and the linked message ID. A channel read-before-send alone
would have a race; the persisted claim prevents concurrent claims. This design
does not claim atomic transactions across both stores.

| Write | Independent confirming read | Inconclusive result | Responsible actor |
|---|---|---|---|
| Pending reply / staff flag | New connection via course.effect; run check reads SQL for current stamp | Registry returns ambiguous error, agent halts; inspect effect ID/status | TA |
| Manual draft / manual flag | Product refresh reads effects and marker | Error displayed; inspect before repeating | Operator |
| Discard/restore/clear/reopen | effects.status plus audit table and updated_by | Inspect state and history | Operator |
| Manual send | channel.messages, effects.channel_id/status and audit row | sending/uncertain held; inspect thread before any correction | Operator |
| Seed/reset | course.records and channel.messages/threads | Re-seed only when intentionally resetting demo/run | Operator/runner |

The compact `experiments/tool_definitions/first_draft.json` is a retained design
variant for a future three-call comparison. It was not used for a measured
baseline. The rewritten definitions add purpose, namespace consistency, argument
constraints, explicit empty-result semantics, semantic IDs, and response bounds.
There are no observed real-model definition failures yet. Controlled probes
cover Lecture 3's categories: wrong arguments (never-stops and direct malformed
calls), wrong tool (unknown-tool and off-plan probes), misinterpreted results
(unsupported draft), and missing call (SaysDone false finish). These are tests,
not measurements of real model error rates.

Examples are useful for `course_create_flag`, where choosing a valid but wrong
reason is plausible; its switch supplies typical and missing-evidence examples.
They add little to `course_get_question`, whose only input is an already supplied
ID. Strict mode is a candidate for `course_create_flag` to constrain required
fields and the reason enum; it does not establish the truth of a search query or
a reply. A fake malformed enum demonstrates local validation, not provider
strict-mode efficacy. `strict.flag` is off by default because no provider is
selected or verified. The candidate has one strict tool, zero optional inputs,
zero union inputs, and one nested level below its argument object. Its object is
closed, both parameters required, and no nullable transformation is needed.
Provider support, vendor limits and source/date verification remain pending;
no claim that strict mode is active is made. `tool_overhead --schema-only`
counts the current selection; the unit test checks the candidate selection.

Run `python -m experiments.analysis.tool_overhead` after configuring a real
provider and price row. The three calls use identical system/user text and the
same registry request format, once without tools, once with the compact variant,
and once with rewritten definitions. Output records provider-reported input
usage including cached input, actual serving model, settings digest, cost and
token deltas; no character-based token estimate is substituted.
