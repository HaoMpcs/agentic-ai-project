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
    rows = course.effects()
    handled = {x["question_id"] for x in rows if x["status"] not in ("discarded", "cleared")}
    result = [{"id": q["id"], "summary": f"{q['kind']}: {q['topic']}", "status": "new",
               "since": q["received_at"]} for q in course.records("question") if q["id"] not in handled]
    result += [{"id": x["id"], "summary": x["question_id"], "status": x["status"]}
               for x in rows if x["status"] in ("pending", "open", "uncertain", "sending")]
    return result
