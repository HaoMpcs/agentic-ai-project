"""Recompute five free stop probes; these are tests, not an improvement arm."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import statistics
import unittest
from pathlib import Path

from harness import ROOT
from harness.trace import now


def measure():
    from tests.test_controls import ControlTests
    case = ControlTests("test_five_stops_interrupt_model_wait_before_any_write")
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(unittest.TestSuite([case]))
    if not result.wasSuccessful():
        raise RuntimeError(output.getvalue())
    samples = case.stop_samples
    times = [s["refused_call_latency_s"] for s in samples]
    sources = ["policy/controls.py", "policy/state.py", "policy/hook.py", "policy/messages.py",
               "policy/approvals.py", "policy/disclosure.py", "policy/escalations.py",
               "sandbox/course.py", "channel/__init__.py", "policy/autonomy.yaml", "agent/tools.py",
               "agent/bounds.py", "agent/service.py", "tests/test_controls.py",
               "experiments/analysis/stop_check.py"]
    return {"kind": "free_stop_control_test", "measured_at": now(), "model_api_calls": 0,
            "description": "Five stops during a blocked free model request, followed by a refused registry probe; no sandbox writes.",
            "sample_n": len(samples), "samples": samples,
            "median_refused_call_latency_s": statistics.median(times), "max_refused_call_latency_s": max(times),
            "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = json.dumps(measure(), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report)
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
