# Author: Jingyu Huang (CNetID: jyhuang28).
"""Free backends for Part A's recovery, loading and program tests."""
import json
from tests.fakes import GoodAgent


class RuntimeAgent(GoodAgent):
    def create(self, *, system, messages, tools):
        if "plan_schema" in messages[0]["content"]:
            return super().create(system=system, messages=messages, tools=tools)
        context = json.loads(messages[0]["content"])
        results = [json.loads(block["content"]) for message in messages if isinstance(message["content"], list)
                   for block in message["content"] if block.get("type") == "tool_result"]
        done = {r["effect"]["question_id"] for r in results if "effect" in r}
        pending = [q for q in context["authorized_questions"] if q["id"] not in done]
        if not pending:
            return self.response(text="Done; inspect the recorded effects.")
        offered = {tool["name"] for tool in tools}
        if "course_find_tools" in offered and not {"course_search_materials", "course_read_document", "course_create_reply", "course_create_flag"} <= offered:
            return self.response(name="course_find_tools", args={"query": "course"})
        combined = []
        for question in pending:
            selected = []
            for result in results:
                if "question" in result and result["question"]["id"] == question["id"]:
                    selected.append(result)
                elif "documents" in result and all(d["topic"] == question["topic"] for d in result["documents"]):
                    selected.append(result)
                elif "document" in result and result["document"]["topic"] == question["topic"]:
                    selected.append(result)
            first = {"role": "user", "content": json.dumps({**context, "authorized_questions": [question]})}
            block = {"role": "user", "content": [{"type": "tool_result", "content": json.dumps(r)} for r in selected]}
            content, stop, model, usage = super().create(system=system, messages=[first, block], tools=tools)
            combined.extend(content)
        return combined, "tool_use", model, usage



class ProgramAgent(GoodAgent):
    def create(self, *, system, messages, tools):
        if len(messages) > 1:
            return self.response(text="DONE")
        ids = json.loads(messages[0]["content"])["question_ids"]
        source = f'''results = []
for qid in {ids!r}:
    q = tool("course_get_question", {{"question_id": qid}})["question"]
    found = tool("course_search_materials", {{"query": q["topic"]}})["documents"]
    d = tool("course_read_document", {{"document_id": found[0]["id"]}})["document"]
    effect = tool("course_create_reply", {{"question_id": qid, "body": d["answer"], "source_ids": [d["id"]]}})
    results = results + [effect["effect"]["id"]]
return results'''
        return self.response(text=source)
