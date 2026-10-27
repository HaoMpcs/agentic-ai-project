"""Scripted free backends for branch and failure tests; never evaluation evidence."""
from __future__ import annotations

import json
import time
from harness.client import Usage


def step(sid, tool, args, deps, expected):
    return {"id": sid, "tool": tool, "arguments": args, "dependencies": deps, "expected": expected}


def valid_plan(metadata):
    steps = []
    for i, q in enumerate(metadata):
        prefix = f"q{i}"
        get, search, read, reply = [f"{prefix}_{s}" for s in ("get", "search", "read", "reply")]
        steps += [step(get, "course_get_question", {"question_id": q["id"]}, [], "question.id exists"),
                  step(search, "course_search_materials", {"query": q["topic"]}, [get], "documents count observed"),
                  step(read, "course_read_document", {"document_id": f"$fill:{search}.documents.0.id"}, [search], "document facts available"),
                  step(reply, "course_create_reply", {"question_id": q["id"], "body": f"$fill:{read}.document.answer",
                       "source_ids": [f"$fill:{read}.document.id"]}, [get, read], "effect.status is pending")]
    return {"steps": steps}


class GoodAgent:
    free = True

    def __init__(self, settings=None):
        self.calls = 0
        self.bad_drafts = 0

    def response(self, *, text=None, name=None, args=None):
        self.calls += 1
        content = [{"type": "text", "text": text}] if text is not None else [
            {"type": "tool_use", "id": f"fake-{self.calls}", "name": name, "input": args}]
        return content, "end_turn" if text is not None else "tool_use", "says-done", Usage(100, 20)

    def plan(self, context):
        return valid_plan(context["questions"])

    def create(self, *, system, messages, tools):
        if "plan_schema" in messages[0]["content"]:
            context, _ = json.JSONDecoder().raw_decode(messages[0]["content"])
            return self.response(text=json.dumps(self.plan(context)))
        initial = json.loads(messages[0]["content"])
        metadata = initial["authorized_questions"]
        results = []
        for message in messages:
            if isinstance(message["content"], list):
                results.extend(json.loads(b["content"]) for b in message["content"] if b.get("type") == "tool_result")
        q = metadata[0]
        qid = q["id"]
        if any("effect" in r for r in results):
            return self.response(text="Finished; verify the environment.")
        if not any("question" in r for r in results):
            return self.response(name="course_get_question", args={"question_id": qid})
        searches = [r["documents"] for r in results if "documents" in r]
        if not searches:
            return self.response(name="course_search_materials", args={"query": q["topic"]})
        if not searches[-1] or q["topic"] == "conflict":
            return self.response(name="course_create_flag", args={"question_id": qid,
                       "reason": "conflicting_sources" if q["topic"] == "conflict" else "missing_information"})
        docs = [r["document"] for r in results if "document" in r]
        read_ids = {x["id"] for x in docs}
        for doc in searches[-1]:
            if doc["id"] not in read_ids:
                return self.response(name="course_read_document", args={"document_id": doc["id"]})
        body = " ".join(d["answer"] for d in docs)
        body = self.draft(body, results)
        return self.response(name="course_create_reply", args={"question_id": qid, "body": body,
                                                               "source_ids": [d["id"] for d in docs]})

    def draft(self, body, results):
        return body


class BadPlanner(GoodAgent):
    def plan(self, context):
        return {"steps": [{"id": "broken", "tool": "publish", "arguments": {}, "dependencies": ["later"], "expected": ""}]}


class OffPlanPlanner(GoodAgent):
    def create(self, **kwargs):
        return self.response(name="course_create_reply", args={"question_id": "SYN-Q-deadline", "body": "skip plan", "source_ids": []})


class RevisingPlanner(GoodAgent):
    def plan(self, context):
        if "previous_plan" not in context:
            return valid_plan(context["questions"])
        plan = context["previous_plan"]
        executed = context["executed"]
        index = len(executed)
        previous = plan["steps"][index - 1]
        qid = plan["steps"][index + 1]["arguments"]["question_id"]
        get_id = previous["dependencies"][0]
        plan["steps"][index:index + 2] = [step(previous["id"] + "_flag", "course_create_flag",
            {"question_id": qid, "reason": "missing_information"}, [get_id, previous["id"]], "staff flag exists")]
        return plan


class BadRevision(RevisingPlanner):
    def plan(self, context):
        plan = super().plan(context)
        if "previous_plan" in context:
            plan["steps"][0]["arguments"]["question_id"] = "SYN-Q-other"
        return plan


class CorrectingAgent(GoodAgent):
    def draft(self, body, results):
        if not any("error" in r for r in results):
            return "Greedy search always guarantees the optimal solution."
        assert any("Unsupported text" in r.get("error", "") for r in results), "revision requires actionable repair fact"
        return body


class NeverCorrect(GoodAgent):
    def draft(self, body, results):
        return "Greedy search always guarantees the optimal solution."


class HugeUsage(GoodAgent):
    def create(self, **kwargs):
        content, reason, name, usage = super().create(**kwargs)
        return content, reason, name, Usage(40000, 20)


class SlowAgent(GoodAgent):
    def create(self, **kwargs):
        time.sleep(0.15)
        return super().create(**kwargs)
