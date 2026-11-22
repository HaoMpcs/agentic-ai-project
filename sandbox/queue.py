"""The work waiting, for the app's queue page.

waiting() returns one dict per item your system has not finished: a new message
to handle, a request on hold, a record to review. Each needs an `id`; `summary`,
`status` and `since` are shown if present, and any other field is shown too.
The queue page adds the threads that wait for an outside reply and anything
waiting for approval, so leave those out.
"""

from __future__ import annotations


def waiting() -> list[dict]:
    from sandbox import course
    from policy import approvals
    from policy import escalations
    from policy import controls
    from policy import messages
    rows = course.effects()
    handled = {x["question_id"] for x in rows if x["status"] not in ("discarded", "cleared")}
    result = [{"id": q["id"], "summary": f"{q['kind']}: {q['topic']}", "status": "new",
               "since": q["received_at"]} for q in course.records("question") if q["id"] not in handled]
    result += [{"id": x["id"], "summary": x["question_id"], "status": x["status"]}
               for x in rows if x["status"] in ("pending", "open", "uncertain", "sending")]
    result += [{"id": x["id"], "summary": f"{x['payload']['tool']} for {x['payload']['arguments']['question_id']}",
                "status": x["status"], "since": x["created_at"], "session_id": x["session_id"], "run_id": x["run_id"]}
               for x in approvals.records(("executing", "uncertain", "blocked", "failed"))]
    result += [{"id": x["id"], "summary": "Write outcome unknown; TA inspection required",
                "status": x["status"], "since": x["created_at"], "session_id": x["session_id"],
                "run_id": x["run_id"], "over_cap": x["over_cap"], "timed_out": x["timed_out"],
                "deadline": x["deadline"], "console_command": "/escalations"}
               for x in escalations.records()]
    result += [{"id": x["run_id"], "summary": "Operator-controlled run", "status": x["status"],
                "since": x["updated_at"], "session_id": x["session_id"]}
               for x in controls.runs() if x["status"] in ("stopped", "awaiting_continuation", "rollback_partial")]
    result += [{"id": f"message-{x['id']}", "summary": x["text"][:160],
                "status": f"{x['kind']}/{x['status']}", "since": x["created_at"],
                "session_id": x["session_id"], "run_id": x["run_id"]}
               for x in messages.records() if x["status"] in ("pending", "observed", "executing", "held")]
    return result
