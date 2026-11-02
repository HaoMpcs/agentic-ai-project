"""Recompute historical Assignment 1-3 evidence without models or archived code.

    python -m experiments.analysis.assignment_evidence

The retained source files are copied from user-supplied archives. Their hashes
are checked first. These results never enter the project's results/ arms.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from statistics import mean

import yaml

from harness import ROOT

EVIDENCE = ROOT / "experiments/assignment_evidence"
ISSUES = set(range(4201, 4207))


def verify_sources(root):
    manifest = json.loads((root / "manifest.json").read_text())
    for name, entry in manifest["files"].items():
        data = (root / name).read_bytes()
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"Historical evidence changed: {name}")
    return manifest


def json_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def answer(body):
    fields = {}
    for key in ("label", "file"):
        match = re.search(rf"^\s*{key}:\s*(.+)$", body, re.I | re.M)
        fields[key] = match[1].strip().strip("`'\"") if match else None
    if fields["label"]:
        fields["label"] = fields["label"].lower()
    if fields["file"]:
        path = fields["file"].replace("\\", "/").rstrip(".,;")
        path = re.sub(r"^(?:\./|fixtures/repo/|repo/)", "", path)
        fields["file"] = "none" if path.lower() in ("none", "n/a", "-") else path
    return fields


def grounded(comments, expected):
    return len(comments) == 1 and answer(comments[0]["body"]) == expected


def load_runs(root):
    runs = []
    for path in sorted((root / "runs").glob("*.jsonl")):
        if path.name.endswith(".calls.jsonl"):
            continue
        rows = json_lines(path)
        if not rows or rows[0].get("type") != "run_start" or rows[-1].get("type") != "run_end":
            raise ValueError(f"Incomplete retained run: {path}")
        if rows[0].get("backend") != "openai-compatible" or rows[0]["issue"] not in ISSUES:
            raise ValueError(f"Unexpected development or fake run: {path}")
        runs.append((path, rows))
    return runs


def check_slots(runs, sweeps, first_sweep=1):
    slots = [(rows[0]["issue"], rows[0]["sweep"]) for _, rows in runs]
    expected = {(issue, sweep) for issue in ISSUES for sweep in range(first_sweep, first_sweep + sweeps)}
    if len(slots) != len(set(slots)) or set(slots) != expected:
        raise ValueError("Historical arm has missing or duplicate evaluation slots")


def inputs(root):
    truth = yaml.safe_load((root / "fixtures/answers.yaml").read_text())["eval"]
    comments = json_lines(root / "tracker/comments.jsonl")
    return truth, comments


def compare_report(actual, reported, fields):
    for name in fields:
        expected, observed = reported[name], actual[name]
        equal = (math.isclose(observed, expected, abs_tol=1e-10, rel_tol=1e-10)
                 if isinstance(expected, float) else observed == expected)
        if not equal:
            raise ValueError(f"Archived report disagrees on {name}: {observed} != {expected}")


def assignment1(root):
    truth, comments = inputs(root)
    reported = json.loads((root / "reports/LAB_01.json").read_text())
    result = {}
    for way in ("workflow", "agent"):
        runs = [run for run in load_runs(root) if run[1][0]["way"] == way]
        check_slots(runs, 10)
        outcomes, costs, tokens, latencies, sequences = {}, [], [], [], []
        per_issue = Counter({str(i): 0 for i in ISSUES})
        for _, rows in runs:
            h = rows[0]
            posted = [c for c in comments if c["run_id"] == h["run_id"] and c["issue"] == h["issue"]]
            ok = grounded(posted, truth[h["issue"]])
            outcomes[(h["issue"], h["sweep"])] = ok
            per_issue[str(h["issue"])] += int(ok)
            calls = [e for e in rows if e["type"] == "model_call"]
            costs.append(sum(e.get("cost_usd") or 0 for e in calls))
            tokens.append(sum(e["usage"]["prompt_tokens"] + e["usage"]["output_tokens"] for e in calls))
            latencies.append(rows[-1]["elapsed_s"])
            sequences.append(tuple(e["name"] for e in rows if e["type"] == "tool_call"))
        result[way] = {"runs": len(runs), "passes": sum(outcomes.values()), "per_issue": dict(per_issue),
                       "mean_cost_usd": mean(costs), "mean_total_tokens": mean(tokens),
                       "p50_latency_s": sorted(latencies)[math.ceil(len(runs) * .5) - 1],
                       "p95_latency_s": sorted(latencies)[math.ceil(len(runs) * .95) - 1],
                       "distinct_tool_sequences": len(set(sequences))}
        compare_report(result[way], reported["results"][way],
                       ("runs", "passes", "per_issue", "mean_cost_usd", "p50_latency_s", "p95_latency_s"))
    c, agent = result["workflow"]["mean_cost_usd"], result["agent"]["mean_cost_usd"]
    qualifying = [i for i in ISSUES if result["workflow"]["per_issue"][str(i)] < 5
                  and result["agent"]["per_issue"][str(i)] >= 5]
    f = len(qualifying) / len(ISSUES)
    result["cost_comparison"] = {"m": agent / c, "qualifying_issues": qualifying, "f_family_share": f,
                                 "extra_cost_per_run_usd": agent - c,
                                 "extra_cost_divided_by_family_share_usd": (agent - c) / f,
                                 "oracle_blended_usd": c * (1 - f) + f * agent,
                                 "f_definition": "share of issue families with workflow <5/10 and agent >=5/10; not this project's f or r"}
    compare_report({"m": agent / c, "f": f},
                   {"m": reported["analysis"]["m_agent_over_workflow_cost"], "f": reported["analysis"]["f"]}, ("m", "f"))
    return result


def assignment2(root):
    truth, comments = inputs(root)
    reported = json.loads((root / "reports/LAB_02.json").read_text())["results"]
    groups = {key: [] for key in ("agent", "planned_off", "planned_self", "planned_external")}
    for run in load_runs(root):
        h = run[1][0]
        key = "agent" if h["way"] == "agent" else "planned_" + h["critique"]
        groups[key].append(run)
    result = {}
    for key, runs in groups.items():
        check_slots(runs, 3)
        passes = repeats = changed = fixed = broken = held = revisions = off_plan = rounds = 0
        per_issue = Counter({str(i): 0 for i in ISSUES})
        tokens, latencies, plan_shares, critique_shares = [], [], [], []
        for _, rows in runs:
            h = rows[0]
            posted = [c for c in comments if c["run_id"] == h["run_id"] and c["issue"] == h["issue"]]
            ok = grounded(posted, truth[h["issue"]])
            passes += ok
            per_issue[str(h["issue"])] += int(ok)
            calls = [e for e in rows if e["type"] == "model_call"]
            prompts = sum(e["usage"]["prompt_tokens"] for e in calls)
            tokens.append(prompts + sum(e["usage"]["output_tokens"] for e in calls))
            plan_shares.append(sum(e["usage"]["prompt_tokens"] for e in calls if e.get("purpose") in ("plan", "revise")) / prompts if prompts else 0)
            critique_shares.append(sum(e["usage"]["prompt_tokens"] for e in calls if e.get("purpose") == "critique") / prompts if prompts else 0)
            latencies.append(rows[-1]["elapsed_s"])
            signatures = [(e["name"], json.dumps(e.get("input") or {}, sort_keys=True)) for e in rows if e["type"] == "tool_call"]
            repeats += len(signatures) != len(set(signatures))
            revisions += sum(e["type"] == "revision" for e in rows)
            off_plan += sum(e["type"] == "off_plan" for e in rows)
            critiques = [e for e in rows if e["type"] == "critique"]
            rounds += len(critiques)
            if any(e.get("changed") for e in critiques):
                changed += 1
                initially_right = answer(critiques[0].get("draft") or "") == truth[h["issue"]]
                fixed += not initially_right and ok
                broken += initially_right and not ok
            held += bool(critiques) and critiques[-1].get("result") == "fail" and not posted
        planned, critiqued = key != "agent", key in ("planned_self", "planned_external")
        row = {"runs": len(runs), "passes": passes, "per_issue": dict(per_issue), "mean_tokens": mean(tokens),
               "p50_latency_s": sorted(latencies)[math.ceil(len(runs) * .5) - 1],
               "max_latency_s": max(latencies), "runs_with_repeat": repeats,
               "plan_overhead_share": mean(plan_shares) if planned else None,
               "critique_overhead_share": mean(critique_shares) if critiqued else None,
               "off_plan": off_plan if planned else None,
               "revisions_mean": revisions / len(runs) if planned else None,
               "rounds_mean": rounds / len(runs) if critiqued else None,
               "drafts_changed": changed if critiqued else None,
               "drafts_fixed": fixed if critiqued else None,
               "drafts_broken": broken if critiqued else None,
               "drafts_held": held if critiqued else None}
        compare_report(row, reported[key], tuple(row))
        result[key] = row
    return result


def assignment3(root):
    reported = json.loads((root / "reports/LAB_03.json").read_text())
    truth = yaml.safe_load((root / "fixtures/answers.yaml").read_text())["eval"]
    result = {}
    with sqlite3.connect((root / "tracker/tracker.db").resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        for arm, mode in (("harness", "derived"), ("control", "uuid")):
            runs = [run for run in load_runs(root) if run[1][0]["switches"]["key_mode"] == mode]
            # The archived control was the second pair of sweeps, numbered 3/4.
            check_slots(runs, 2, first_sweep=1 if mode == "derived" else 3)
            duplicates = maximum = grounded_count = conditional_pr = timeouts = escalated = 0
            calls = 0
            for _, rows in runs:
                h = rows[0]
                comments = [dict(x) for x in db.execute("SELECT * FROM comments WHERE run_id=? AND issue=?", (h["run_id"], h["issue"]))]
                prs = list(db.execute("SELECT * FROM prs WHERE run_id=?", (h["run_id"],)))
                duplicates += len(comments) > 1
                maximum = max(maximum, len(comments))
                grounded_count += grounded(comments, truth[h["issue"]])
                posted_file = answer(comments[0]["body"])["file"] if comments else None
                matching = [p for p in prs if p["state"] == "open" and p["branch"] == f"repomind/issue-{h['issue']}"]
                conditional_pr += len(prs) == len(matching) == int(posted_file not in (None, "none"))
                timeouts += db.execute("SELECT COUNT(*) FROM attempts WHERE run_id=? AND outcome='timeout_after_commit'", (h["run_id"],)).fetchone()[0]
                escalated += any(e["type"] == "end" and e.get("terminal_reason") == "escalated" for e in rows)
                calls += sum(e["type"] == "model_call" for e in rows)
            row = {"runs": len(runs), "comments_per_run_max": maximum, "duplicate_comment_runs": duplicates,
                   "prs_correct_runs": conditional_pr, "committed_timeouts": timeouts,
                   "escalated": escalated, "triage_passes": grounded_count}
            compare_report(row, reported["writes"][arm], tuple(row))
            result[arm] = {**row, "model_calls": calls}
    result["tool_surface_reported"] = {k: reported["surface"][k] for k in
                                       ("tokens_before", "tokens_after", "list_tokens_before", "list_tokens_after")}
    result["tool_surface_status"] = "Reported historical API measurements; raw standalone provider responses not retained. Not a current-project measurement."
    return result


def summarize(root=EVIDENCE):
    root = Path(root)
    manifest = verify_sources(root)
    return {"kind": manifest["kind"], "owner": manifest["owner"], "source_read_date_utc": manifest["read_date"],
            "verified_source_files": len(manifest["files"]),
            "assignment1": assignment1(root / "assignment1"),
            "assignment2": assignment2(root / "assignment2"),
            "assignment3": assignment3(root / "assignment3"),
            "assignment4": "Reviewed for scope; no memory, compaction or restart recovery imported into M1."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = summarize()
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
