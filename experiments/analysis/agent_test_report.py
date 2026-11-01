"""Run responsibility-2 tests and retain free ScratchTest evidence.

    python -m experiments.analysis.agent_test_report

This is a mechanism test report, not a real-model baseline or improvement arm.
The original runner records and traces are copied unchanged before scratch
folders disappear. Production state, model settings and switches are untouched.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import unittest

from harness import ROOT, records
from harness.trace import read_trace


TESTS = [
    "tests.test_course.CourseTests",
    "tests.test_planning.PlanningTests",
    "tests.test_agent_contracts.AgentContractTests",
    "tests.test_course.RegistryTests.test_orphan_repeat_out_of_order_and_extra_detectors",
    "tests.test_course.RegistryTests.test_executor_refuses_changed_arguments_extra_and_out_of_order",
    "tests.test_analysis.AnalysisTests",
]
EVENTS = {"routing", "agent_bounds", "plan", "plan_validation", "plan_checkpoint",
          "plan_outcome", "plan_execution_diff", "draft_critique", "off_plan",
          "repeat_call", "end", "write_verification", "model_inflight_timeout"}


def source_files():
    """Fingerprint the working files used by this scope, including new tests."""
    paths = [ROOT / name for name in ("settings.yaml", "switches.yaml", "pricing.yaml", "run.py")]
    for folder in ("agent", "checks", "sandbox", "tests", "tasks", "harness", "channel"):
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.suffix in (".py", ".yaml"))
    paths.extend((ROOT / "experiments/analysis").glob("*.py"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(set(paths))}


def test_cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from test_cases(item)
        else:
            yield item


def event_lines(trace):
    return [{"line": n, "type": event["type"]}
            for n, event in enumerate(read_trace(trace), 1) if event["type"] in EVENTS]


def retain_runs(test, destination, retained, sessions):
    original = test.run_task
    original_teardown = test.tearDown

    def run_and_retain(*args, **kwargs):
        record = original(*args, **kwargs)
        if not record["free"]:
            raise AssertionError("Mechanism evidence must use a free fake model.")
        trace = next(test.tmp.rglob(record["run_id"] + ".trace.jsonl"))
        record_path = trace.with_name(record["run_id"] + ".json")
        target = destination / test.id() / record["arm"]
        target.mkdir(parents=True, exist_ok=True)
        copied_trace = target / trace.name
        shutil.copy2(trace, copied_trace)
        shutil.copy2(record_path, target / record_path.name)
        retained.append({
            "test": test.id(), "run_id": record["run_id"], "task": record["task"],
            "free": record["free"], "task_check_passed": record["passed"],
            "end_reasons": record["end_reasons"], "model_calls": record["model_calls"],
            "record": str((target / record_path.name).relative_to(ROOT)),
            "trace": str(copied_trace.relative_to(ROOT)),
            "events": event_lines(copied_trace),
        })
        return record

    def retain_session_traces():
        try:
            for trace in sorted((test.tmp / "traces").glob("*.jsonl")):
                target = destination / test.id() / "sessions" / trace.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(trace, target)
                sessions.append({"test": test.id(), "trace": str(target.relative_to(ROOT)),
                                 "events": event_lines(target)})
        finally:
            original_teardown()

    # Wrap this test instance only. Tests still execute through ScratchTest's
    # own run_task; exporting happens after the run and before tearDown cleanup.
    test.run_task = run_and_retain
    test.tearDown = retain_session_traces


class ReportResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = []

    def startTest(self, test):
        super().startTest(test)
        self.started = time.perf_counter()
        self.current = {"test": test.id(), "status": "running", "problems": []}
        self.rows.append(self.current)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.current["status"] = "passed"

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.problem(test, err, "failed")

    def addError(self, test, err):
        super().addError(test, err)
        self.problem(test, err, "error")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.problem(subtest, err, "failed")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.current.update(status="skipped", problems=[reason])

    def problem(self, test, err, status):
        self.current["status"] = status
        self.current["problems"].append(self._exc_info_to_string(err, test))

    def stopTest(self, test):
        self.current["duration_s"] = round(time.perf_counter() - self.started, 4)
        super().stopTest(test)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/reports" / ("agent-tests-" + stamp))
    args = parser.parse_args()
    output = args.output.resolve()
    artifacts = ROOT / "results/_free" / output.name
    if output.exists() or artifacts.exists():
        parser.error("Output already exists; choose a fresh --output to preserve earlier evidence.")
    output.mkdir(parents=True)
    suite = unittest.defaultTestLoader.loadTestsFromNames(TESTS)
    retained, sessions = [], []
    for test in test_cases(suite):
        retain_runs(test, artifacts, retained, sessions)
    fingerprint = source_files()
    with (output / "unit-tests.log").open("w") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=ReportResult).run(suite)
    checks = []
    for command in (["make", "test"], ["make", "check"], ["git", "diff", "--check"]):
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        log = output / ("-".join(command).replace("--", "") + ".log")
        log.write_text(run.stdout + run.stderr)
        checks.append({"command": command, "exit_code": run.returncode,
                       "log": str(log.relative_to(ROOT))})
    unchanged = fingerprint == source_files()
    passed = result.wasSuccessful() and all(c["exit_code"] == 0 for c in checks) and unchanged
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Responsibility 2: routing, agent bounds, planning, critique and detectors",
        "kind": "free mechanism tests; not an official baseline or improvement pass",
        "source": records.source(ROOT), "source_files_sha256": fingerprint,
        "source_unchanged_during_test": unchanged, "passed": passed,
        "tests_run": result.testsRun, "statuses": dict(Counter(r["status"] for r in result.rows)),
        "tests": result.rows, "project_checks": checks, "runs": retained, "session_traces": sessions,
        "retained_run_count": len(retained), "all_retained_runs_free": all(r["free"] for r in retained),
        "limitations": ["Fake usage, costs and timings do not measure real model performance.",
                        "Negative task checks can be expected successes of refusal tests.",
                        "Real baseline, a pushed prediction and measured pass arms remain separate work."],
    }
    path = output / "summary.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"passed": passed, "tests_run": result.testsRun, "statuses": report["statuses"],
                      "retained_runs": len(retained), "summary": str(path.relative_to(ROOT)),
                      "project_checks": checks}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
