"""Validated model-selected plans; deterministic executor and bounded revision."""
from __future__ import annotations

import copy
import json
import re

from harness import schema
from agent.bounds import Halt
from agent.tools import SCHEMAS, WRITES, constraints, obj

MAX_PLAN_STEPS = 16
MAX_REPLANS = 1
MAX_REVISIONS = 1
PLAN_SCHEMA = obj({"steps": {"type": "array", "items": obj({
    "id": {"type": "string"}, "tool": {"type": "string"}, "arguments": {"type": "object"},
    "dependencies": {"type": "array", "items": {"type": "string"}}, "expected": {"type": "string"}})}})
FILL = re.compile(r"^\$fill:([A-Za-z][A-Za-z0-9_-]*)\.([A-Za-z0-9_.]+)$")


def placeholders(value):
    if isinstance(value, str) and value.startswith("$fill"):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from placeholders(child)
    elif isinstance(value, list):
        for child in value:
            yield from placeholders(child)


def validate(plan, question_ids):
    problems = schema.errors(plan, PLAN_SCHEMA)
    if problems:
        return problems
    steps = plan["steps"]
    if not 1 <= len(steps) <= MAX_PLAN_STEPS:
        return [f"Plan needs 1..{MAX_PLAN_STEPS} steps."]
    seen, depended, terminals = {}, set(), []
    for step in steps:
        sid, name, deps = step["id"], step["tool"], step["dependencies"]
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", sid) or sid in seen:
            problems.append(f"Invalid or repeated step ID {sid}.")
        if name not in SCHEMAS or name in ("course_list_flags", "course_status"):
            problems.append(f"Unknown or unauthorized plan tool {name}.")
        if any(dep not in seen for dep in deps) or len(deps) != len(set(deps)):
            problems.append(f"{sid}: dependencies must name distinct earlier steps (no forward/order errors).")
        for placeholder in placeholders(step["arguments"]):
            match = FILL.fullmatch(placeholder)
            if not match or match[1] not in deps:
                problems.append(f"{sid}: a $fill must reference an explicit earlier dependency.")
        if not step["expected"].strip():
            problems.append(f"{sid}: missing observable expected outcome.")
        if name in SCHEMAS:
            # Validate structure with runtime values represented by schema-shaped
            # stand-ins. Full content and authorization validation occurs again
            # after resolving placeholders, before dispatch.
            args = copy.deepcopy(step["arguments"])
            for field, spec in SCHEMAS[name]["properties"].items():
                if field in args and isinstance(args[field], str) and args[field].startswith("$fill:"):
                    args[field] = "SYN-placeholder"
            problems += schema.errors(args, SCHEMAS[name]) + constraints(args, SCHEMAS[name])
        qid = step["arguments"].get("question_id")
        if qid is not None and qid not in question_ids:
            problems.append(f"{sid}: question outside authorized request.")
        if name in WRITES:
            terminals.append(qid)
        depended.update(deps)
        seen[sid] = step
    for step in steps:
        if step["id"] not in depended and step["tool"] not in WRITES:
            problems.append(f"Orphan step {step['id']}: its result has no dependent consumer.")
    if sorted(terminals) != sorted(question_ids):
        problems.append("Plan must produce exactly one terminal action for every requested question.")
    return problems


def resolve(value, outputs):
    if isinstance(value, str) and value.startswith("$fill"):
        match = FILL.fullmatch(value)
        if not match:
            raise ValueError("Malformed runtime placeholder.")
        node = outputs[match[1]]
        for field in match[2].split("."):
            node = node[int(field)] if isinstance(node, list) else node[field]
        return node
    if isinstance(value, dict):
        return {k: resolve(v, outputs) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, outputs) for v in value]
    return value


def execution_diff(plan, actual):
    expected = [s["id"] for s in plan["steps"]]
    seen, executed, extra, out_of_order = set(), [], [], []
    for call in actual:
        sid = call.get("plan_step")
        if sid not in expected:
            extra.append(sid)
            continue
        if sid not in seen:
            if expected.index(sid) != len(executed):
                out_of_order.append(sid)
            seen.add(sid)
            executed.append(sid)
    return {"executed": executed, "skipped": [s for s in expected if s not in seen],
            "extra": extra, "out_of_order": out_of_order, "aligned": not extra and not out_of_order}


class Executor:
    def __init__(self, registry, bounds, metadata, operator_request):
        self.registry, self.bounds = registry, bounds
        self.trace = registry.trace
        self.metadata, self.request = metadata, operator_request
        self.plan = {"steps": []}
        self.outputs = {}
        self.executed = []
        self.actual = []
        self.version = 0
        self.revisions = 0

    def propose(self, *, revision=False):
        # Safe metadata/results only: never include student-written text.
        context = {"operator_request": self.request,
                   "questions": self.metadata, "max_steps": MAX_PLAN_STEPS,
                   "plan_schema": PLAN_SCHEMA,
                   "fill_format": "$fill:<dependency_id>.<result.path>; e.g. $fill:search.documents.0.id"}
        if revision:
            context.update(previous_plan=self.plan, executed=self.executed,
                           observed={sid: safe_status(out) for sid, out in self.outputs.items()})
        feedback = ""
        for attempt in range(MAX_REPLANS + 1):
            response = self.bounds.model(system=("Return only a JSON plan matching plan_schema. No tool calls. "
                "Choose steps to read each question, search its topic, read matching documents and create one pending reply or staff flag. "
                "Use dependencies and $fill for unknown document IDs/answer text. Every read needs a consuming dependent step. "
                "Each step has id, tool, arguments, dependencies, expected (observable outcome). "
                "For a revision preserve every executed prefix step exactly; use a missing_information flag when search found zero. "
                "Never publish. The planner receives trusted metadata only."),
                messages=[{"role": "user", "content": json.dumps(context) + feedback}],
                tools=self.registry.definitions(planner=True), purpose="revise_plan" if revision else "plan")
            try:
                if response.tool_calls:
                    self.trace.event("off_plan", stage="planner", calls=[c.name for c in response.tool_calls])
                    raise ValueError("Planner must return a plan, not execute a tool.")
                candidate = json.loads(response.text)
                problems = validate(candidate, [m["id"] for m in self.metadata])
                if revision and candidate.get("steps", [])[:len(self.executed)] != self.plan["steps"][:len(self.executed)]:
                    problems.append("Revision changed an executed prefix step.")
                if problems:
                    raise ValueError("; ".join(problems))
            except (ValueError, TypeError) as exc:
                feedback = "\nRejected plan; repair: " + str(exc)[:1000]
                self.trace.event("plan_validation", accepted=False, attempt=attempt + 1, revision=revision, reason=str(exc)[:1000])
                continue
            self.version += 1
            self.plan = candidate
            self.trace.plan(self.version, candidate, revision=revision)
            self.trace.event("plan_validation", accepted=True, attempt=attempt + 1, revision=revision)
            return
        raise Halt("revision_rejected" if revision else "plan_rejected", "Validation/re-plan bound; no further execution.")

    def dispatch(self, step, name, arguments):
        expected = self.plan["steps"][len(self.executed)]
        expected_args = resolve(expected["arguments"], self.outputs)
        if step["id"] != expected["id"] or name != expected["tool"] or arguments != expected_args:
            self.trace.event("off_plan", step_id=step["id"], name=name, input=arguments)
            raise Halt("off_plan", "Extra, changed or out-of-order tool refused before dispatch.")
        self.bounds.tick()
        result = self.registry.call(name, arguments, step=self.bounds.steps, plan_step=step["id"], caller="executor")
        self.actual.append({"plan_step": step["id"]})
        if result.is_error:
            raise Halt("plan_tool_error", result.data["error"])
        self.outputs[step["id"]] = result.data
        self.executed.append(step["id"])
        self.trace.event("plan_step", step_id=step["id"], status="executed", version=self.version)
        return result

    def run(self):
        try:
            self.propose()
            while len(self.executed) < len(self.plan["steps"]):
                step = self.plan["steps"][len(self.executed)]
                try:
                    args = resolve(step["arguments"], self.outputs)
                except (KeyError, IndexError, ValueError, TypeError):
                    raise Halt("plan_fill_error", "A dependency did not produce the referenced result.") from None
                result = self.dispatch(step, step["tool"], args)
                if step["tool"] == "course_search_materials":
                    count = len(result.data["documents"])
                    self.trace.event("plan_checkpoint", name="sources_available", passed=count > 0,
                                     count=count, step_id=step["id"], version=self.version)
                    if count == 0:
                        if self.revisions >= MAX_REVISIONS:
                            raise Halt("revision_limit")
                        self.revisions += 1
                        self.propose(revision=True)
            return "plan_completed"
        finally:
            diff = execution_diff(self.plan, self.actual)
            self.trace.event("plan_execution_diff", **diff, versions=self.version, revisions=self.revisions)
            for sid in diff["skipped"]:
                self.trace.event("plan_step", step_id=sid, status="skipped", version=self.version)


def safe_status(output):
    if "documents" in output:
        return {"count": len(output["documents"]), "ids": [x["id"] for x in output["documents"]]}
    if "question" in output:
        return {"id": output["question"]["id"], "status": "read"}
    if "document" in output:
        return {"id": output["document"]["id"], "status": "read"}
    if "effect" in output:
        return {"id": output["effect"]["id"], "status": output["effect"]["status"]}
    return {"status": "observed"}
