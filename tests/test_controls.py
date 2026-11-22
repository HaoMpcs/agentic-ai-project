"""Operator interrupts are tested against environment effects and real threads."""
from __future__ import annotations

import json
import threading
from datetime import datetime
from unittest import mock

from agent import service
from agent.tools import Registry
from harness import runtime, turns
from policy import approvals, controls, state
from sandbox import course, seed
from tests.support import ScratchTest


class BlockingClient:
    free = True
    total_tokens = 0

    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.finished = threading.Event()

    def create(self, **kwargs):
        self.started.set()
        self.release.wait(5)
        self.finished.set()
        raise RuntimeError("Free blocking fixture finished after operator stop")


class ControlTests(ScratchTest):
    def setUp(self):
        super().setUp()
        seed.reset()
        seed.seed(None)
        runtime.configure(backend="tests.fakes:GoodAgent")

    def flag(self, registry, qid):
        registry.call("course_get_question", {"question_id": qid})
        result = registry.call("course_create_flag", {"question_id": qid, "reason": "missing_information"})
        self.assertFalse(result.is_error, result.data)
        return result.data["effect"]

    def test_five_stops_interrupt_model_wait_before_any_write(self):
        latencies = []
        self.stop_samples = []
        for index in range(5):
            session = f"model-stop-{index}"
            client = BlockingClient()
            replies = []
            with mock.patch("harness.runtime.client", return_value=client):
                thread = threading.Thread(target=lambda: replies.append(turns.operator_turn(session, "Process SYN-Q-concept")))
                thread.start()
                self.assertTrue(client.started.wait(2))
                try:
                    stopped = turns.operator_turn(session, "/stop")
                    self.assertIn("stopped", stopped.text)
                    thread.join(2)
                    self.assertFalse(thread.is_alive())
                    self.assertIn("Run stopped", replies[0].text)
                finally:
                    client.release.set()
                    thread.join(2)
                    self.assertTrue(client.finished.wait(2))
            events = runtime.trace(session).lines()
            observed = [e for e in events if e["type"] == "stop_observed"]
            self.assertEqual(len(observed), 1)
            # Probe the next registry call as well as the interrupted model wait.
            registry = Registry(session, ["SYN-Q-concept"])
            self.assertTrue(registry.call("course_search_materials", {"query": "search"}).data["stopped"])
            refused = next(e for e in runtime.trace(session).lines() if e["type"] == "stop_refused")
            with state.db() as conn:
                flag_at = conn.execute("SELECT updated_at FROM stops WHERE run_id=?", (session,)).fetchone()[0]
            seconds = (datetime.fromisoformat(refused["at"]) - datetime.fromisoformat(flag_at)).total_seconds()
            latencies.append(seconds)
            self.stop_samples.append({"session": session, "flag_at": flag_at, "first_refused_call_at": refused["at"],
                                      "refused_call_latency_s": seconds, "first_observed_latency_s": observed[0]["latency_s"]})
            self.assertFalse(course.effects())
        self.assertEqual(len(latencies), 5)
        self.assertLess(max(latencies), 1.0)

    def test_inflight_write_finishes_recorded_and_resume_waits_for_old_turn(self):
        committed = threading.Event()
        release = threading.Event()
        original = Registry._reply
        replies = []

        def slow(registry, args, key):
            result = original(registry, args, key)
            committed.set()
            release.wait(5)
            return result

        with mock.patch.object(Registry, "_reply", slow):
            thread = threading.Thread(target=lambda: replies.append(turns.operator_turn("inflight", "Process SYN-Q-deadline")))
            thread.start()
            self.assertTrue(committed.wait(2))
            try:
                self.assertIn("stopped", turns.operator_turn("inflight", "/stop").text)
                self.assertEqual(len(course.effects()), 1)
                self.assertIn("still finishing", turns.operator_turn("inflight", "/resume").text)
                self.assertTrue(state.is_stopped("inflight"))
            finally:
                release.set()
                thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertIn("Run stopped", replies[0].text)
        row = next(r for r in controls.runs() if r["run_id"] == "inflight")
        saved = json.loads(row["snapshot"])
        writes = [c for c in saved["calls"] if c["action_key"]]
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]["status"], "completed")
        self.assertEqual(writes[0]["action_key"], course.effects()[0]["action_key"])
        self.assertEqual(saved["task"]["question_ids"], ["SYN-Q-deadline"])
        events = runtime.trace("inflight").lines()
        self.assertLess(next(i for i,e in enumerate(events) if e["type"] == "run_live"),
                        next(i for i,e in enumerate(events) if e["type"] == "tool_call" and e["name"] == "course_create_reply"))

    def test_stop_withdraws_gate_resume_reasks_and_old_answer_cannot_execute(self):
        turns.operator_turn("review", "/limit drafts approval")
        turns.operator_turn("review", "Process SYN-Q-deadline")
        old = service.pending_approvals()[0]
        turns.operator_turn("review", "/stop")
        self.assertFalse(service.pending_approvals())
        self.assertEqual(approvals.get(old["id"])["status"], "withdrawn")
        self.assertIn("already withdrawn", turns.decide_approval(old["id"], True, session_id="review").text)
        self.assertFalse(course.effects())
        self.assertIn("newly issued approval", turns.operator_turn("review", "/resume").text)
        new = service.pending_approvals()[0]
        self.assertNotEqual(old["id"], new["id"])
        self.assertIn("already superseded", turns.decide_approval(old["id"], True, session_id="review").text)
        turns.decide_approval(new["id"], True, session_id="review")
        self.assertEqual(len(course.effects()), 1)

    def test_cancel_is_permanent_and_preserves_effects(self):
        registry = Registry("cancel", ["SYN-Q-deadline"])
        effect = self.flag(registry, "SYN-Q-deadline")
        turns.operator_turn("cancel", "/stop")
        reply = turns.operator_turn("cancel", "/cancel")
        self.assertIn("cancelled permanently", reply.text)
        self.assertEqual(course.effect(effect["id"])["status"], "open")
        self.assertIn("nothing was changed", turns.operator_turn("cancel", "/resume").text)
        self.assertTrue(state.is_stopped("cancel"))
        self.assertTrue(registry.call("course_status", {"question_id": "SYN-Q-deadline"}).is_error)

    def test_rollback_compensates_owned_writes_newest_first_and_is_idempotent(self):
        registry = Registry("rollback", ["SYN-Q-deadline", "SYN-Q-concept"])
        first = self.flag(registry, "SYN-Q-deadline")
        last = self.flag(registry, "SYN-Q-concept")
        turns.operator_turn("rollback", "/stop")
        reply = turns.operator_turn("rollback", "/rollback")
        self.assertLess(reply.text.index(last["id"]), reply.text.index(first["id"]))
        self.assertEqual([e["status"] for e in course.effects()], ["cleared", "cleared"])
        with course.db() as conn:
            before = conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        turns.operator_turn("rollback", "/rollback rollback")
        with course.db() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0], before)
        decisions = [e for e in runtime.trace("rollback").lines() if e["type"] == "policy_decision"]
        self.assertTrue(any(e["action_class"] == "operator_compensate/owned" for e in decisions))

    def test_rollback_reports_none_for_sent_message_and_denies_foreign_effect(self):
        registry = Registry("sent", ["SYN-Q-deadline"])
        registry.call("course_get_question", {"question_id": "SYN-Q-deadline"})
        registry.call("course_read_document", {"document_id": "SYN-DOC-deadline"})
        args = {"question_id": "SYN-Q-deadline", "body": course.record("document", "SYN-DOC-deadline")["answer"],
                "source_ids": ["SYN-DOC-deadline"]}
        result = registry.call("course_create_reply", args)
        effect_id = result.data["effect"]["id"]
        turns.operator_turn("sent", f"/send {effect_id}")
        pending = service.pending_approvals()[0]
        turns.decide_approval(pending["id"], True, session_id="sent")
        turns.operator_turn("sent", "/stop")
        self.assertIn(": none", turns.operator_turn("sent", "/rollback").text)
        self.assertEqual(course.effect(effect_id)["status"], "sent")
        foreign = course.create_effect("flag", "SYN-Q-deadline", reason="missing_information", key="foreign-key")
        self.assertIn(": none", registry.compensate(foreign["id"]))
        self.assertEqual(course.effect(foreign["id"])["status"], "open")

    def test_outside_stop_is_not_operator_control(self):
        registry = Registry("outside", ["SYN-Q-deadline"])
        turns.outside_reply("SYN-Q-deadline", "/stop", sender="student")
        self.assertFalse(state.is_stopped("outside"))
        self.flag(registry, "SYN-Q-deadline")
        turns.operator_turn("outside", "/stop")
        turns.outside_reply("SYN-Q-deadline", "/resume", sender="student")
        self.assertTrue(state.is_stopped("outside"))
        self.assertEqual(len(course.effects()), 1)

    def test_stopped_state_and_call_snapshot_survive_new_process(self):
        import subprocess
        import sys
        registry = Registry("persist", ["SYN-Q-deadline"])
        self.flag(registry, "SYN-Q-deadline")
        turns.operator_turn("persist", "/stop")
        script = "from policy import controls,state; import json; print(json.dumps({'stopped':state.is_stopped('persist'),'calls':controls.calls('persist')}))"
        completed = subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)
        data = json.loads(completed.stdout)
        self.assertTrue(data["stopped"])
        self.assertTrue(any(c["action_key"] for c in data["calls"]))

    def test_late_stop_after_completed_turn_does_not_count(self):
        turns.operator_turn("done", "Process SYN-Q-deadline")
        self.assertIn("No live", turns.operator_turn("done", "/stop").text)
        self.assertFalse(state.is_stopped("done"))

    def test_stop_cannot_be_bypassed_between_hook_and_dispatch(self):
        registry = Registry("race", ["SYN-Q-deadline"])
        registry.call("course_get_question", {"question_id": "SYN-Q-deadline"})
        registry.hook = lambda name, args: state.set_stopped("race", True) or True
        handler = mock.Mock()
        registry.handlers["course_create_flag"] = handler
        result = registry.call("course_create_flag", {"question_id": "SYN-Q-deadline", "reason": "missing_information"})
        self.assertTrue(result.data["stopped"])
        handler.assert_not_called()
        self.assertFalse(course.effects())

    def test_rollback_policy_can_deny_and_compensation_key_is_not_reapplied(self):
        from policy import hook
        registry = Registry("policy-rollback", ["SYN-Q-deadline"])
        effect = self.flag(registry, "SYN-Q-deadline")
        turns.operator_turn("policy-rollback", "/stop")
        rules = hook.load_policy()
        rules["operator_compensate/owned"]["column"] = "prohibited"
        with mock.patch.object(hook, "load_policy", return_value=rules):
            self.assertIn(": none", turns.operator_turn("policy-rollback", "/rollback").text)
        self.assertEqual(course.effect(effect["id"])["status"], "open")
        turns.operator_turn("policy-rollback", "/rollback policy-rollback")
        self.assertEqual(course.effect(effect["id"])["status"], "cleared")
        course.update_status(effect["id"], "open", "operator explicitly reopened")
        turns.operator_turn("policy-rollback", "/rollback policy-rollback")
        self.assertEqual(course.effect(effect["id"])["status"], "open")

    def test_resume_lifts_flag_without_replaying_model_or_completed_effect(self):
        registry = Registry("resume", ["SYN-Q-deadline"])
        self.flag(registry, "SYN-Q-deadline")
        turns.operator_turn("resume", "/stop")
        turns.operator_turn("resume", "/limit sends deny")
        self.assertEqual(state.limits("resume")[0]["target"], "sends")
        with mock.patch.object(service, "agent_loop", side_effect=AssertionError("no guessed replay")):
            reply = turns.operator_turn("resume", "/resume")
            self.assertIn("awaits Part 1", turns.operator_turn("resume", "Process SYN-Q-concept").text)
        self.assertIn("Part 1", reply.text)
        self.assertFalse(state.is_stopped("resume"))
        self.assertEqual(len(course.effects()), 1)
        self.assertTrue(registry.call("course_search_materials", {"query": "deadline"}).is_error)
        self.assertTrue(any(e["type"] == "run_resumed" for e in runtime.trace("resume").lines()))

    def test_stop_all_runs_in_session_and_resume_only_named_run(self):
        Registry("multi", [], run_id="multi:1")
        Registry("multi", [], run_id="multi:2")
        turns.operator_turn("multi", "/stop")
        self.assertTrue(state.is_stopped("multi:1"))
        self.assertTrue(state.is_stopped("multi:2"))
        turns.operator_turn("multi", "/resume multi:1")
        self.assertFalse(state.is_stopped("multi:1"))
        self.assertTrue(state.is_stopped("multi:2"))
