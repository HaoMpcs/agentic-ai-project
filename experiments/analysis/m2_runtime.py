# Author: Jingyu Huang (CNetID: jyhuang28).
"""Recompute Part A's retained mechanism evidence, never an evaluation arm.

    python -m experiments.analysis.m2_runtime experiments/reports/m2-part-a-20261121/recovery
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from harness import ROOT


def summarize(folder):
    folder = Path(folder)
    cases = []
    events = Counter()
    for path in sorted(folder.glob("*.json")):
        state = json.loads(path.read_text())
        if "after_resume" not in state:
            continue
        trace = [json.loads(line) for line in path.with_suffix(".trace.jsonl").read_text().splitlines()]
        counts = Counter(row["question_id"] for row in state["after_resume"])
        replayed = [event for event in trace[state["crash_trace_lines"]:]
                    if event["type"] == "mcp_request" and event["metadata"]["run_key"] == state["run_key"]]
        for event in trace:
            if event["type"] in ("call_reused", "mcp_request", "tool_search", "compensation"):
                events[event["type"]] += 1
            if event["type"] == "write_resolution":
                events["write_" + event["verdict"]] += 1
        cases.append({"task": path.stem, "effects_before": len(state["before"]),
                      "effects_after_crash": len(state["after_crash"]),
                      "effects_after_resume": len(state["after_resume"]),
                      "duplicate_effects": sum(max(0, n-1) for n in counts.values()),
                      "completed_execution_calls_repeated": len(replayed)})
    if not cases:
        raise ValueError("No retained recovery cases found; run the documented evidence capture first.")
    evidence = ROOT / "experiments/assignment_evidence/assignment4_runtime"
    provenance = json.loads((evidence / "source.json").read_text())
    for name, record in provenance["files"].items():
        if hashlib.sha256((evidence / name).read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("Assignment 4 report source hash mismatch: " + name)
    homework = json.loads((evidence / "LAB_04.json").read_text())
    matrices = {mode: {"cases": len(homework[mode]),
                      "one_comment_cases": sum(row["comments"] == 1 for row in homework[mode]),
                      "duplicate_comment_cases": sum(row["comments"] > 1 for row in homework[mode])}
                for mode in ("matrix_derived", "matrix_uuid")}
    return {"kind": "free mechanism tests; not a real-model baseline or improvement pass",
            "recovery_cases": len(cases), "duplicates": sum(c["duplicate_effects"] for c in cases),
            "completed_execution_calls_repeated": sum(c["completed_execution_calls_repeated"] for c in cases),
            "cases": cases, "events": dict(events),
            "historical_assignment4_reported_matrices": matrices,
            "historical_source_files_hash_verified": len(provenance["files"])}


def historical_tool_bill():
    """Apply M1's measured default-definition overhead to M1 call counts only."""
    records = [json.loads(path.read_text()) for path in (ROOT / "results/baseline").glob("*.json")]
    counts = [record["model_calls"] for record in records]
    return {"source": "M1 default definitions: 808 API-measured input tokens per call",
            "runs": len(records), "model_calls": sum(counts),
            "mean_calls_per_run": sum(counts)/len(counts),
            "estimated_definition_tokens_per_run": 808*sum(counts)/len(counts),
            "scope": "Historical default surface only, not new M2 measurements or split-role costs"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    print(json.dumps({**summarize(args.folder), "historical_tool_bill": historical_tool_bill()}, indent=2))


if __name__ == "__main__":
    main()
