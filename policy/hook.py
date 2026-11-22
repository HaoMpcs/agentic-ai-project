"""Classify and enforce before dispatch; approval never overrides prohibition."""
from __future__ import annotations

import re
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from harness import ROOT
from policy import state
from sandbox import course

POLICY_PATH = ROOT / "policy" / "autonomy.yaml"


class PolicyBlocked(PermissionError):
    def __init__(self, action_class, column, decision):
        self.action_class, self.column, self.decision = action_class, column, decision
        message = ("Operator approval is required; this operation has not run."
                   if decision == "approval_required" else "This operation is not permitted.")
        super().__init__(message)


def load_policy(path: Path = POLICY_PATH) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("classes"), dict):
        raise ValueError("Invalid autonomy policy")
    review = data.get("review", {})
    if (not isinstance(review, dict) or type(review.get("daily_cap")) is not int or review["daily_cap"] < 0
            or type(review.get("hold_timeout_seconds")) is not int or review["hold_timeout_seconds"] <= 0):
        raise ValueError("Invalid review budget policy")
    ZoneInfo(review["timezone"])
    for name, rule in data["classes"].items():
        if (not isinstance(name, str) or not isinstance(rule, dict)
                or rule.get("column") not in ("independent", "requires_approval", "prohibited")
                or not isinstance(rule.get("reason"), str) or not rule["reason"].strip()):
            raise ValueError("Invalid action class")
    return data["classes"]


def classify(name: str, args: dict, caller: str) -> str:
    if name == "course_send_reply":
        from policy import disclosure
        if not disclosure.valid(args["body"]):
            return f"{name}/missing_disclosure"
        try:
            if disclosure.prepare(args["effect_id"]) != args:
                return f"{name}/invalid_draft"
        except ValueError:
            return f"{name}/invalid_draft"
        return f"{name}/student_reply"
    if name == "course_read_document":
        try:
            doc = course.record("document", args["document_id"])
        except ValueError:
            return "course_read_document/restricted"
        suffix = "public_active" if doc.get("active") and doc.get("visibility") == "public" else "restricted"
        return f"{name}/{suffix}"
    if name == "course_create_reply":
        q = course.record("question", args["question_id"])
        if q["kind"] in ("personal", "exception"):
            return f"{name}/staff_only"
        if "SYN-PRIVATE-" in args["body"]:
            return f"{name}/private_content"
        if q["kind"] == "unauthorized" and (args["body"] != course.REFUSAL or args["source_ids"]):
            return f"{name}/invalid_refusal"
        return f"{name}/pending"
    suffixes = {"course_get_question": "selected", "course_search_materials": "public",
                "course_search_public_answers": "public", "course_create_flag": "internal",
                "course_status": "selected",
                "operator_compensate": "owned" if caller == "operator" else "unknown",
                "course_list_flags": "operator" if caller == "operator" else "non_operator"}
    return f"{name}/{suffixes.get(name, 'unknown')}"


def enforce(name, args, *, caller, session_id, run_id, trace, approval_id=None, operator_compensation=False):
    compensating = operator_compensation and name == "operator_compensate" and caller == "operator"
    from policy import controls
    # A persisted stop is consulted before reading/classifying any target record.
    if state.is_stopped(run_id) and not compensating:
        from policy import controls
        controls.observe(run_id, trace)
        trace.event("policy_decision", action_class="run/stopped", column="prohibited",
                    decision="stopped", tool=name, caller=caller, control_run_id=run_id)
        raise PolicyBlocked("run/stopped", "prohibited", "stopped")
    from policy import escalations
    held_status = next((r["status"] for r in controls.runs(session_id)
                        if r["run_id"] == run_id and r["status"] in ("awaiting_continuation", "message_held")), None)
    if not compensating and held_status:
        trace.event("policy_decision", action_class=f"run/{held_status}", column="prohibited",
                    decision="held", tool=name, caller=caller, control_run_id=run_id)
        raise PolicyBlocked(f"run/{held_status}", "prohibited", "held")
    if not compensating and any(r["run_id"] == run_id and r["session_id"] == session_id for r in escalations.records()):
        trace.event("policy_decision", action_class="run/escalated", column="prohibited",
                    decision="held", tool=name, caller=caller, control_run_id=run_id)
        raise PolicyBlocked("run/escalated", "prohibited", "held")
    rules = load_policy()
    action_class = classify(name, args, caller)
    rule = rules.get(action_class)
    column = rule["column"] if rule else "prohibited"
    # Operator limits may narrow an allowed action, never relax a prohibition.
    matched = []
    if column != "prohibited" and name in ("course_create_reply", "course_create_flag", "course_send_reply"):
        targets = {"writes"} | ({"drafts"} if name == "course_create_reply" else set())
        if name == "course_send_reply":
            targets.add("sends")
        matched = [r for r in state.limits(session_id) if r["target"] in targets]
        if matched:
            mode = "deny" if any(r["mode"] == "deny" for r in matched) else "approval"
            action_class = f"operator_limit/{mode}"
            column = rules[action_class]["column"]
            # Changing the file must not turn an operator restriction into allow.
            if mode == "deny" or column != "requires_approval":
                column = "prohibited"
    decision = {"independent": "allow", "requires_approval": "approval_required", "prohibited": "deny"}[column]
    from policy import approvals
    if decision != "deny" and not compensating:
        holds = [r for r in approvals.records(("pending", "executing", "uncertain"))
                 if r["run_id"] == run_id and r["session_id"] == session_id and r["id"] != approval_id]
        unrelated = [r for r in holds if not (
            r["status"] == "pending" and decision == "approval_required"
            and r["payload"]["tool"] == name
            and approvals.canonical(r["payload"]["arguments"]) == approvals.canonical(args))]
        if unrelated:
            action_class, column, decision = "run/awaiting_approval", "prohibited", "deny"
    if decision != "deny" and approval_id:
        if approvals.authorizes(approval_id, session_id=session_id, run_id=run_id, name=name, args=args):
            decision = "allow"
        else:
            decision = "deny"
    trace.event("policy_decision", action_class=action_class, column=column, decision=decision,
                tool=name, caller=caller, control_run_id=run_id,
                limit_targets=[r["target"] for r in matched], approval_id=approval_id)
    if decision != "allow":
        raise PolicyBlocked(action_class, column, decision)


def operator_limit(session_id, text, trace) -> str | None:
    """Called only on trusted console input, before model calls and session locks.

    Deliberately exact commands/phrases: no model or heuristic decides authority.
    Unknown /limit syntax is consumed and explained rather than sent to a model.
    """
    normalized = " ".join(text.strip().lower().rstrip(".!?").split())
    aliases = {"send nothing until i have read it": ("sends", "approval"),
               "do not create drafts until i approve": ("drafts", "approval")}
    match = re.fullmatch(r"/limit (drafts|writes|sends) (approval|deny)", normalized)
    setting = match.groups() if match else aliases.get(normalized)
    if setting:
        target, mode = setting
        state.set_limit(session_id, target, mode, text[:4000])
        trace.event("operator_limit", target=target, mode=mode, source="trusted_operator")
        suffix = " Automated sends still require explicit draft selection and review." if target == "sends" else ""
        outcome = "require approval" if mode == "approval" else "are prohibited"
        return f"Session rule saved: {target} {outcome}." + suffix
    if normalized.startswith("/limit"):
        return "Use /limit drafts|writes|sends approval|deny. Rules apply to this console session."
    return None
