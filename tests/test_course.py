from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import channel
from agent import service
from agent.bounds import Bounds, Halt
from agent.planning import Executor, execution_diff, validate
from agent.tools import Registry, SCHEMAS, constraints
from harness import runtime, turns
from harness.trace import read_trace
from sandbox import course, seed
from tests.fakes import valid_plan
from tests.support import ScratchTest


class CourseTests(ScratchTest):
    def demo(self):
        seed.reset()
        seed.seed(None)
        runtime.configure(backend="tests.fakes:GoodAgent")

    def trace(self, record):
        paths = list(self.tmp.rglob(record["run_id"] + ".trace.jsonl"))
        return read_trace(paths[0])

    def test_all_main_and_development_tasks_through_runner(self):
        for path in sorted(Path("tasks").rglob("*.yaml")):
            with self.subTest(task=path):
                backend = "tests.fakes:RevisingPlanner" if "checkpoint" in str(path) else "tests.fakes:GoodAgent"
                record = self.run_task(path, path.stem, backend=backend)
                self.assertTrue(record["passed"], record.get("check_reason", record))
                self.assertEqual(record["outcome"], "completed")
                self.assertTrue(record["free"])

    def test_reset_seed_deterministic_and_private_synthetic(self):
        self.demo()
        first = course.records("question")
        self.assertEqual(len(channel.messages("SYN-Q-deadline")), 1)
        self.assertTrue(channel.messages("SYN-Q-deadline")[0].seeded)
        self.assertTrue(all(x["id"].startswith("SYN-") and x["synthetic"] for x in course.records("private_student")))
        seed.reset()
        self.assertFalse(course.records("question"))
        self.assertFalse(channel.threads())
        seed.seed(None)
        self.assertEqual(first, course.records("question"))
        self.assertIn("-05:00", course.record("clock", "SYN-CLOCK")["now"])

    def test_independent_check_negative_controls(self):
        task = "tasks/deadline_question.yaml"
        self.assertFalse(self.run_check(task, lambda run: None, replies=["Done successfully."])["passed"])
        def plant(run, body=None, stamp=None):
            doc = course.record("document", "SYN-DOC-deadline")
            course.create_effect("reply", "SYN-Q-deadline", body=body or doc["answer"],
                                 source_ids=[doc["id"]], key="planted")
        self.assertTrue(self.run_check(task, plant)["passed"])
        self.assertFalse(self.run_check(task, lambda run: plant(run, "It is due November 3."))["passed"])
        self.assertFalse(self.run_check(task, lambda run: (plant(run), channel.send("SYN-Q-deadline", "Not authorized")))["passed"])
        self.assertFalse(self.run_check(task, lambda run: (plant(run), channel.send("SYN-Q-unrelated", "Not authorized")))["passed"])
        with mock.patch("sandbox.course.stamp", return_value="another-run"):
            self.assertFalse(self.run_check(task, plant)["passed"])
        self.assertFalse(self.run_check(task, lambda run: (plant(run), course.create_effect("reply", "SYN-Q-deadline",
                         body=course.record("document", "SYN-DOC-deadline")["answer"], source_ids=["SYN-DOC-deadline"], key="duplicate")))["passed"])

    def test_bound_never_stopping_agent(self):
        record = self.run_task("tasks/conceptual_question.yaml", "step-bound")
        self.assertIn("agent_step_limit", record["end_reasons"])
        self.assertFalse(record["passed"])
        self.assertTrue(any(x["type"] == "repeat_call" for x in self.trace(record)))

    def test_token_and_wall_bounds(self):
        record = self.run_task("tasks/conceptual_question.yaml", "token-bound", backend="tests.fakes:HugeUsage")
        self.assertIn("agent_token_budget", record["end_reasons"])
        self.assertNotIn("token_budget", record["end_reasons"])
        with mock.patch("agent.bounds.WALL_SECONDS", 0.03):
            record = self.run_task("tasks/conceptual_question.yaml", "wall-bound", backend="tests.fakes:SlowAgent")
        self.assertIn("agent_wall_clock", record["end_reasons"])
        self.assertFalse(course.effects())

    def test_says_done_does_not_satisfy_effect_check(self):
        record = self.run_task("tasks/conceptual_question.yaml", "false-finish", backend="harness.scripted:SaysDone")
        self.assertFalse(record["passed"])
        self.assertIn("false_finish", record["end_reasons"])

    def test_valid_plan_order_and_no_untrusted_planner_input(self):
        record = self.run_task("tasks/batch_questions.yaml", "good-plan", backend="tests.fakes:GoodAgent")
        self.assertTrue(record["passed"])
        lines = self.trace(record)
        plan_index = next(i for i,x in enumerate(lines) if x["type"] == "plan")
        first_call = next(i for i,x in enumerate(lines) if x["type"] == "tool_call")
        self.assertLess(plan_index, first_call)
        diff = next(x for x in lines if x["type"] == "plan_execution_diff")
        self.assertTrue(diff["aligned"])
        self.assertEqual(len(diff["executed"]), 12)
        self.assertEqual(diff["skipped"], [])

    def test_invalid_plan_replan_bound_and_no_writes(self):
        record = self.run_task("tasks/batch_questions.yaml", "bad-plan", backend="tests.fakes:BadPlanner")
        self.assertIn("plan_rejected", record["end_reasons"])
        self.assertEqual(sum(x["type"] == "plan_validation" for x in self.trace(record)), 2)
        self.assertFalse(course.effects())

    def test_planner_tool_call_refused(self):
        record = self.run_task("tasks/batch_questions.yaml", "off-plan", backend="tests.fakes:OffPlanPlanner")
        self.assertIn("plan_rejected", record["end_reasons"])
        self.assertTrue(any(x["type"] == "off_plan" for x in self.trace(record)))
        self.assertFalse(course.effects())

    def test_revision_only_on_observed_failed_checkpoint(self):
        record = self.run_task("tasks/dev/checkpoint_revision.yaml", "revision", backend="tests.fakes:RevisingPlanner")
        self.assertTrue(record["passed"], record)
        plans = [x for x in self.trace(record) if x["type"] == "plan"]
        self.assertEqual([p["version"] for p in plans], [1,2])
        self.assertEqual(plans[0]["plan"]["steps"][:2], plans[1]["plan"]["steps"][:2])
        self.assertTrue(any(x["type"] == "plan_checkpoint" and not x["passed"] and x["count"] == 0 for x in self.trace(record)))

    def test_invalid_revision_never_executes_and_labels_skipped(self):
        record = self.run_task("tasks/dev/checkpoint_revision.yaml", "bad-revision", backend="tests.fakes:BadRevision")
        self.assertIn("revision_rejected", record["end_reasons"])
        self.assertFalse(course.effects())
        self.assertTrue(any(x["type"] == "plan_step" and x["status"] == "skipped" for x in self.trace(record)))

    def test_critique_correct_revised_and_bound(self):
        for backend, passed, end in (("GoodAgent",True,"agent_completed"),("CorrectingAgent",True,"agent_completed"),
                                     ("NeverCorrect",False,"critique_limit")):
            with self.subTest(backend=backend):
                record = self.run_task("tasks/conceptual_question.yaml", backend.lower(), backend="tests.fakes:"+backend)
                self.assertEqual(record["passed"], passed, record)
                self.assertIn(end, record["end_reasons"])
                self.assertEqual(len(course.effects()), int(passed))
                critics = [x for x in self.trace(record) if x["type"] == "draft_critique"]
                self.assertEqual(len(critics), {"GoodAgent":1,"CorrectingAgent":2,"NeverCorrect":3}[backend])
                if backend == "CorrectingAgent":
                    self.assertIn("Unsupported", critics[0]["reason"])
                    self.assertTrue(critics[1]["passed"])

    def test_critique_ablation_is_independently_scored(self):
        record = self.run_task("tasks/conceptual_question.yaml", "critic-off", backend="tests.fakes:NeverCorrect",
                               overrides=["critique.reply=off"])
        self.assertFalse(record["passed"])
        self.assertEqual(len(course.effects()),1)

    def test_follow_up_and_repeated_request_never_duplicate(self):
        self.demo()
        first = turns.operator_turn("S-test", "Process SYN-Q-deadline")
        next_ = turns.operator_turn("S-test", "What did you do?")
        turns.operator_turn("S-test", "Process SYN-Q-deadline")
        self.assertIn("SYN-Q-deadline", first.text)
        self.assertEqual(first.text,next_.text)
        self.assertEqual(len(course.effects()),1)
        self.assertEqual(course.effects()[0]["stamp"],"S-test")

    def test_ambiguous_student_text_does_not_override_trusted_routing(self):
        record = self.run_task("tasks/unauthorized_question.yaml", "misrouting", backend="tests.fakes:GoodAgent")
        self.assertTrue(record["passed"])
        self.assertEqual(record["model_calls"],0)
        self.assertTrue(any(x["type"] == "routing" and x["route"] == "workflow" for x in self.trace(record)))

    def test_outside_replies_and_approvals_preserve_m1_contract(self):
        self.demo()
        self.assertEqual(service.on_outside_reply("SYN-Q-deadline", "Send it now").text, "")
        self.assertEqual(service.pending_approvals(),[])
        self.assertFalse(course.effects())


class RegistryTests(ScratchTest):
    def setUp(self):
        super().setUp()
        seed.reset()
        seed.seed(None)
        runtime.configure(backend="tests.fakes:GoodAgent")
        self.reg = Registry("registry", ["SYN-Q-deadline", "SYN-Q-private"])

    def read_before_write(self):
        self.reg.call("course_get_question", {"question_id": "SYN-Q-deadline"})
        self.reg.call("course_read_document", {"document_id": "SYN-DOC-deadline"})
        return {"question_id": "SYN-Q-deadline", "body": course.record("document", "SYN-DOC-deadline")["answer"],
                "source_ids": ["SYN-DOC-deadline"]}

    def test_invalid_call_errors_and_trace(self):
        cases = [("course_get_question", {}, "required"),
                 ("course_get_question", {"question_id": 4}, "string"),
                 ("course_get_question", {"question_id": "SYN-Q-other"}, "outside"),
                 ("course_search_materials", {"query": "x"*161}, "length"),
                 ("course_create_flag", {"question_id": "SYN-Q-deadline", "reason": "invented"}, "one of"),
                 ("publish", {}, "Unknown tool")]
        for name,args,repair in cases:
            with self.subTest(name=name, args=args):
                result = self.reg.call(name,args)
                self.assertTrue(result.is_error)
                self.assertIn(repair,result.data["error"])
        self.assertFalse(course.effects())
        lines=runtime.trace("registry").lines()
        calls=[x for x in lines if x["type"]=="tool_call"]
        self.assertEqual(len(calls),len(cases))
        self.assertTrue(all(x["is_error"] and x["error_class"] and "cost_usd" in x and "latency_s" in x for x in calls))

    def test_case_insensitive_enum_and_idempotent_reworded_action(self):
        self.reg.call("course_get_question", {"question_id": "SYN-Q-deadline"})
        a=self.reg.call("course_create_flag", {"question_id": "SYN-Q-deadline", "reason": "MISSING_INFORMATION"})
        b=self.reg.call("course_create_flag", {"question_id": "SYN-Q-deadline", "reason": "conflicting_sources"})
        self.assertFalse(a.is_error)
        self.assertEqual(a.data,b.data)
        self.assertEqual(len(course.effects()),1)

    def test_fail_closed_hook(self):
        args=self.read_before_write()
        def broken(name,args):raise RuntimeError("hook unavailable")
        self.reg.hook=broken
        result=self.reg.call("course_create_reply",args)
        self.assertTrue(result.is_error)
        self.assertIn("hook failed",result.data["error"])
        self.assertFalse(course.effects())

    def test_transient_retry_once_and_ambiguous_write_no_retry(self):
        args=self.read_before_write()
        original=self.reg.handlers["course_create_reply"]
        counter=[]
        def flaky(a,key):
            counter.append(key)
            if len(counter)==1:raise ConnectionError("temporary")
            return original(a,key)
        self.reg.handlers["course_create_reply"]=flaky
        result=self.reg.call("course_create_reply",args)
        self.assertFalse(result.is_error)
        self.assertEqual(counter[0],counter[1])
        self.assertEqual(len(course.effects()),1)
        seed.reset();seed.seed(None)
        self.reg=Registry("ambiguous",["SYN-Q-deadline"])
        args=self.read_before_write()
        calls=[]
        def uncertain(a,key):
            calls.append(key)
            course.create_effect("reply",a["question_id"],body=a["body"],source_ids=a["source_ids"],key=key)
            raise TimeoutError("after commit")
        self.reg.handlers["course_create_reply"]=uncertain
        result=self.reg.call("course_create_reply",args)
        self.assertEqual(result.error_class,"ambiguous")
        self.assertEqual(len(calls),1)
        self.assertEqual(len(course.effects()),1)

    def test_write_retries_preserve_first_effect(self):
        args=self.read_before_write()
        first=self.reg.call("course_create_reply",args)
        again=self.reg.call("course_create_reply",args)
        self.assertEqual(first.data,again.data)
        self.assertEqual(len(course.effects()),1)
        self.assertIn("idempotency_key",[x for x in self.reg.trace.lines() if x["type"]=="tool_call"][-1])

    def test_result_validation_response_bound_and_private_record_denied(self):
        self.reg.handlers["course_search_materials"]=lambda a,k: {"oops":[]}
        self.assertTrue(self.reg.call("course_search_materials",{"query":"deadline"}).is_error)
        self.assertTrue(self.reg.call("course_read_document",{"document_id":"SYN-STUDENT-001"}).is_error)
        self.assertTrue(self.reg.call("course_read_document",{"document_id":"SYN-DOC-old"}).is_error)
        self.reg.handlers["course_search_public_answers"]=lambda a,k: {"answers":[{"id":"SYN-PUBLIC-big","body":"x"*7000,"source_ids":[]}]}
        self.assertTrue(self.reg.call("course_search_public_answers",{"topic":"late_policy"}).is_error)

    def test_fixed_tool_order_examples_and_strict_shape(self):
        first=self.reg.definitions()
        runtime.configure(backend="tests.fakes:GoodAgent",overrides=["examples.flag=on","strict.flag=on"])
        second=self.reg.definitions()
        self.assertEqual([d["name"] for d in first],[d["name"] for d in second])
        tool=next(d for d in second if d["name"]=="course_create_flag")
        self.assertTrue(tool["strict"])
        self.assertIn("Typical",tool["description"])
        self.assertFalse(tool["input_schema"]["additionalProperties"])
        self.assertEqual(set(tool["input_schema"]["required"]),set(tool["input_schema"]["properties"]))
        self.assertFalse(any(d["name"]=="send" for d in second))
        self.assertTrue(constraints(11,{"minimum":0,"maximum":10}))

    def test_orphan_repeat_out_of_order_and_extra_detectors(self):
        plan=valid_plan([{"id":"SYN-Q-deadline","topic":"deadline"}])
        self.assertEqual(validate(plan,["SYN-Q-deadline"]),[])
        plan["steps"][1]["dependencies"]=[]
        plan["steps"][3]["dependencies"]=["q0_read"]
        self.assertTrue(any("Orphan" in e for e in validate(plan,["SYN-Q-deadline"])))
        diff=execution_diff(plan,[{"plan_step":"q0_search"},{"plan_step":"extra"},{"plan_step":"q0_search"}])
        self.assertIn("q0_search",diff["out_of_order"])
        self.assertEqual(diff["extra"],["extra"])
        self.assertEqual(len(diff["skipped"]),3)
        self.reg.call("course_status",{"question_id":"SYN-Q-deadline"})
        self.reg.call("course_status",{"question_id":"SYN-Q-deadline"})
        self.assertTrue(any(x["type"]=="repeat_call" for x in self.reg.trace.lines()))

    def test_executor_refuses_changed_arguments_extra_and_out_of_order(self):
        bounds=Bounds("executor")
        executor=Executor(self.reg,bounds,[{"id":"SYN-Q-deadline","topic":"deadline"}],"Process it")
        executor.plan=valid_plan(executor.metadata)
        current=executor.plan["steps"][0]
        with self.assertRaises(Halt):
            executor.dispatch(current,"course_get_question",{"question_id":"SYN-Q-private"})
        with self.assertRaises(Halt):
            executor.dispatch(executor.plan["steps"][1],"course_search_materials",{"query":"deadline"})
        self.assertFalse(course.effects())
