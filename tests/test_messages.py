"""Mid-task commands: real threads, sandbox state and deterministic free models."""
from __future__ import annotations

import contextlib
import copy
import json
import subprocess
import sys
import threading
from unittest import mock

from agent import service
from agent.tools import Registry
from harness import runtime, turns
from policy import approvals, controls, messages, state
from sandbox import course, seed
from tests.fakes import GoodAgent
from tests.support import ScratchTest, fixed_run, check_run


class MessageTests(ScratchTest):
    def setUp(self):
        super().setUp()
        seed.reset()
        seed.seed(None)
        runtime.configure(backend="tests.fakes:GoodAgent")

    @contextlib.contextmanager
    def running(self, session="busy", phase="_reply"):
        entered, release = threading.Event(), threading.Event()
        original = getattr(Registry, phase)
        replies, errors = [], []

        def slow(registry, args, key):
            result = original(registry, args, key)
            if not entered.is_set():
                entered.set()
                release.wait(5)
            return result

        def work():
            try:
                replies.append(turns.operator_turn(session, "Process SYN-Q-deadline"))
            except Exception as exc:
                errors.append(exc)

        with mock.patch.object(Registry, phase, slow):
            thread = threading.Thread(target=work)
            thread.start()
            try:
                self.assertTrue(entered.wait(2))
                yield replies
            finally:
                release.set()
                thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_add_keeps_original_effect_once_and_processes_added_case(self):
        with self.running() as replies:
            reply = turns.operator_turn("busy", "/add SYN-Q-private")
            self.assertIn("saved as add", reply.text)
            self.assertEqual(len(course.effects()), 1)
        effects = course.effects()
        self.assertEqual(sorted(e["question_id"] for e in effects), ["SYN-Q-deadline", "SYN-Q-private"])
        self.assertTrue(all(e["status"] == "pending" for e in effects))
        self.assertEqual(messages.records("busy")[0]["status"], "done")
        self.assertIn("SYN-Q-private", replies[0].text)

    def test_add_is_read_before_next_model_call_without_planner_student_text(self):
        entered, release = threading.Event(), threading.Event()
        original = GoodAgent.create
        contexts = []
        errors = []

        def pause(backend, **kwargs):
            contexts.append(copy.deepcopy(kwargs["messages"]))
            if not entered.is_set():
                entered.set()
                release.wait(5)
            return original(backend, **kwargs)

        def work():
            try:
                turns.operator_turn("model-add", "Process SYN-Q-concept")
            except Exception as exc:
                errors.append(exc)

        with mock.patch.object(GoodAgent, "create", pause):
            thread = threading.Thread(target=work)
            thread.start()
            try:
                self.assertTrue(entered.wait(2))
                self.assertIn("saved as add", turns.operator_turn("model-add", "/add SYN-Q-deadline").text)
            finally:
                release.set()
                thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors)
        self.assertGreater(len(contexts), 1)
        self.assertTrue(any("trusted_operator_addition" in str(m["content"]) for m in contexts[1]))
        self.assertEqual(sorted(e["question_id"] for e in course.effects()), ["SYN-Q-concept", "SYN-Q-deadline"])

    def test_replace_before_old_write_produces_only_new_effect(self):
        with self.running(phase="_document") as replies:
            reply = turns.operator_turn("busy", "/replace SYN-Q-private")
            self.assertIn("old task stopped", reply.text)
            self.assertTrue(state.is_stopped("busy"))
        self.assertEqual([e["question_id"] for e in course.effects()], ["SYN-Q-private"])
        self.assertIn("Earlier effects: none", replies[0].text)
        self.assertNotEqual(messages.current_run("busy"), "busy")
        self.assertEqual(next(r for r in controls.runs() if r["run_id"] == "busy")["status"], "replaced")

    def test_replace_rolls_back_prior_effect_then_same_question_has_fresh_key(self):
        with self.running() as replies:
            original = course.effects()[0]
            turns.operator_turn("busy", "/replace --rollback SYN-Q-deadline")
        effects = course.effects()
        self.assertEqual(len(effects), 2)
        self.assertEqual(sorted(e["status"] for e in effects), ["discarded", "pending"])
        self.assertEqual(len({e["action_key"] for e in effects}), 2)
        self.assertIn(original["id"], replies[0].text)
        self.assertIn("discarded", replies[0].text)

    def test_replace_can_compensate_only_selected_owned_effects(self):
        registry = Registry("select", ["SYN-Q-deadline", "SYN-Q-concept"])
        effects = []
        for qid in ("SYN-Q-deadline", "SYN-Q-concept"):
            registry.call("course_get_question", {"question_id": qid})
            effects.append(registry.call("course_create_flag", {"question_id": qid, "reason": "missing_information"}).data["effect"])
        reply = turns.operator_turn("select", f"/replace --undo {effects[0]['id']} SYN-Q-private")
        self.assertIn(effects[0]["id"], reply.text)
        self.assertEqual(course.effect(effects[0]["id"])["status"], "cleared")
        self.assertEqual(course.effect(effects[1]["id"])["status"], "open")
        self.assertEqual(len(course.effects(question_id="SYN-Q-private")), 1)

    def test_default_queue_answers_in_order_after_task_finishes(self):
        with self.running() as replies:
            a = turns.operator_turn("busy", "What did you do?")
            b = turns.operator_turn("busy", "What happened?")
            self.assertIn("saved as queue", a.text)
            self.assertIn("saved as queue", b.text)
            self.assertTrue(all(r["status"] == "pending" for r in messages.records("busy")))
        rows = messages.records("busy")
        self.assertEqual([r["status"] for r in rows], ["done", "done"])
        self.assertTrue(all("SYN-Q-deadline" in r["answer"] for r in rows))
        self.assertLess(replies[0].text.index("Message 1:"), replies[0].text.index("Message 2:"))
        self.assertEqual(len(course.effects()), 1)

    def test_queue_is_bounded_and_stop_bypasses_full_queue(self):
        with self.running(phase="_document"):
            for i in range(messages.QUEUE_LIMIT):
                self.assertIn("saved as queue", turns.operator_turn("busy", f"Status update {i}").text)
            self.assertIn("queue is full", turns.operator_turn("busy", "One more update").text)
            self.assertIn("stopped", turns.operator_turn("busy", "/stop").text)
        self.assertEqual(len(messages.records("busy")), messages.QUEUE_LIMIT)
        self.assertFalse(course.effects())
        self.assertIn("pending", turns.operator_turn("busy", "/messages").text)

    def test_waiting_gate_can_be_replaced_and_old_approval_stays_invalid(self):
        turns.operator_turn("gate", "/limit drafts approval")
        turns.operator_turn("gate", "Process SYN-Q-deadline")
        old = service.pending_approvals()[0]
        turns.operator_turn("gate", "/replace SYN-Q-private")
        new = service.pending_approvals()[0]
        self.assertNotEqual(old["id"], new["id"])
        self.assertEqual(approvals.get(old["id"])["status"], "withdrawn")
        turns.decide_approval(old["id"], True, session_id="gate")
        self.assertFalse(course.effects())
        turns.decide_approval(new["id"], True, session_id="gate")
        self.assertEqual([e["question_id"] for e in course.effects()], ["SYN-Q-private"])

    def test_invalid_replace_does_not_stop_old_task_and_explicit_reject_is_immediate(self):
        with self.running() as replies:
            self.assertIn("Unknown command", turns.operator_turn("busy", "/replacee SYN-Q-private").text)
            self.assertIn("existing inbox", turns.operator_turn("busy", "/replace SYN-Q-invented").text)
            self.assertFalse(state.is_stopped("busy"))
            self.assertIn("rejected immediately", turns.operator_turn("busy", "/reject Do something else").text)
            self.assertFalse(messages.records("busy"))
        self.assertEqual(len(course.effects()), 1)

    def test_operator_limit_phrase_is_not_queued_and_outside_add_is_ignored(self):
        with self.running(phase="_document"):
            reply = turns.operator_turn("busy", "Send nothing until I have read it.")
            self.assertIn("rule saved", reply.text)
            turns.outside_reply("SYN-Q-deadline", "/add SYN-Q-private", sender="student")
            self.assertFalse(messages.records("busy"))
        self.assertEqual([e["question_id"] for e in course.effects()], ["SYN-Q-deadline"])

    def test_pending_queue_survives_new_process_without_executing(self):
        Registry("persistent-inbox", [])
        messages.route("persistent-inbox", "Status please", runtime.trace("persistent-inbox"), busy=True)
        script = "from policy.messages import records; import json; print(json.dumps(records('persistent-inbox')))"
        completed = subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)
        rows = json.loads(completed.stdout)
        self.assertEqual(rows[0]["status"], "pending")
        self.assertFalse(course.effects())

    def test_queue_cannot_delay_stop_command(self):
        reply = turns.operator_turn("session", "/queue /stop")
        self.assertIn("never through the queue", reply.text)
        self.assertFalse(messages.records("session"))

    def test_add_with_fixed_run_and_independent_task_check(self):
        task = "tests/fixtures/midtask_add.yaml"
        with fixed_run(task, "fixed-add", backend="tests.fakes:GoodAgent"):
            with self.running() as replies:
                turns.operator_turn("busy", "/add SYN-Q-private")
            checked = check_run(task, "fixed-add", [replies[0].text])
            self.assertTrue(checked["passed"], checked)
            self.assertEqual(checked["measures"]["midtask_operations"], 1)

    def test_replace_with_fixed_run_and_check_rejects_old_task_write(self):
        task = "tests/fixtures/midtask_replace.yaml"
        with fixed_run(task, "fixed-replace", backend="tests.fakes:GoodAgent"):
            with self.running(phase="_document") as replies:
                turns.operator_turn("busy", "/replace SYN-Q-private")
            checked = check_run(task, "fixed-replace", [replies[0].text])
            self.assertTrue(checked["passed"], checked)
            course.create_effect("flag", "SYN-Q-deadline", reason="missing_information", key="planted-old-task-write")
            self.assertFalse(check_run(task, "fixed-replace")["passed"])

    def test_queued_status_stays_bound_to_old_run_after_replacement(self):
        with self.running():
            turns.operator_turn("busy", "What did you do?")
            turns.operator_turn("busy", "/replace SYN-Q-private")
        queued = next(r for r in messages.records("busy") if r["kind"] == "queue")
        self.assertEqual(queued["status"], "done")
        self.assertIn("SYN-Q-deadline", queued["answer"])
        self.assertNotIn("SYN-Q-private", queued["answer"])

    def test_addition_admission_enforces_combined_limit_and_final_barrier(self):
        q = course.record("question", "SYN-Q-deadline")
        course.put_record("question", {**q, "id": "SYN-Q-fourth"})
        with self.running(phase="_document"):
            self.assertIn("saved as add", turns.operator_turn("busy", "/add SYN-Q-concept SYN-Q-private").text)
            self.assertIn("at most three", turns.operator_turn("busy", "/add SYN-Q-fourth").text)
            turns.operator_turn("busy", "/stop")
        seed.reset()
        seed.seed(None)
        Registry("barrier", ["SYN-Q-deadline"])
        controls.remember_task("barrier", "Process SYN-Q-deadline", ["SYN-Q-deadline"], "workflow")
        self.assertEqual(messages.additions_or_finish("barrier"), [])
        self.assertIn("no active task", turns.operator_turn("barrier", "/add SYN-Q-private").text)

    def test_deferred_error_keeps_original_reply_and_holds_new_task(self):
        original_turn = service._turn

        def fail_deferred(session_id, text, **kwargs):
            if kwargs.get("_run_id"):
                raise RuntimeError("fixture deferred failure")
            return original_turn(session_id, text, **kwargs)

        with mock.patch.object(service, "_turn", fail_deferred):
            with self.running() as replies:
                turns.operator_turn("busy", "Process SYN-Q-private")
        self.assertIn("SYN-Q-deadline", replies[0].text)
        self.assertIn("Deferred message held", replies[0].text)
        self.assertEqual(messages.records("busy")[0]["status"], "held")
        self.assertEqual([e["question_id"] for e in course.effects()], ["SYN-Q-deadline"])
        current = messages.current_run("busy")
        registry = Registry("busy", ["SYN-Q-private"], run_id=current)
        self.assertTrue(registry.call("course_search_materials", {"query": "privacy"}).is_error)
        turns.operator_turn("busy", "/cancel")
        self.assertEqual(messages.records("busy")[0]["status"], "cancelled")
        self.assertEqual(len(course.effects()), 1)
