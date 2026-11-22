"""Independent end-state checks for concurrency fixtures, not assistant claims."""
from __future__ import annotations

from dataclasses import replace

from checks.course import check as course_check
from checks.helpers import connect


def check(run):
    mode = run.task["midtask_mode"]
    task = dict(run.task)
    if mode == "replace":
        task["inputs"] = task["inputs"][1:]
    passed, reason, measures = course_check(replace(run, task=task))
    if not passed:
        return passed, reason, measures
    with connect(run, "autonomy.sqlite3") as conn:
        count = conn.execute("SELECT COUNT(*) FROM operator_messages WHERE run_id=? AND kind=? AND status='done'",
                             (run.run_id, mode)).fetchone()[0]
    if count != 1:
        return False, "Expected one completed explicit mid-task operation", measures
    measures["midtask_operations"] = count
    return True, "Mid-task operation and current-run effects match ground truth", measures
