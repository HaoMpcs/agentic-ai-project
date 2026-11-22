"""Per-action gate: immutable review, restart, policy recheck and sandbox effects."""
from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from fastapi.testclient import TestClient

import channel
from agent import service
from agent.tools import Registry
from app.main import app
from harness import runtime, turns
from policy import approvals, state
from sandbox import course, queue, seed
from tests.support import ScratchTest


class ApprovalTests(ScratchTest):
    def setUp(self):
        super().setUp()
        seed.reset()
        seed.seed(None)
        runtime.configure(backend="tests.fakes:GoodAgent")

    def request(self):
        turns.operator_turn("review-session", "/limit drafts approval")
        reply = turns.operator_turn("review-session", "Process SYN-Q-deadline")
        self.assertIn("approval", reply.text)
        self.assertFalse(course.effects())
        self.assertEqual(len(service.pending_approvals()), 1)
        return service.pending_approvals()[0]

    def decide(self, item, approved=True):
        return turns.decide_approval(item["id"], approved, "test decision", session_id=item["session_id"])

    def test_gate_waits_queue_and_approve_runs_exact_call_with_original_key(self):
        item = self.request()
        row = approvals.get(item["id"])
        expected = row["payload"]["arguments"]
        self.assertFalse(course.effects())
        with TestClient(app) as client:
            self.assertIn("1 waiting", client.get("/queue").text)
            page = client.get("/approvals").text
            self.assertIn("Exact effect", page)
            self.assertIn("source_check_passed", page)
        reply = self.decide(item)
        self.assertIn("saved reply", reply.text)
        self.assertEqual(service.pending_approvals(), [])
        effects = course.effects()
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["body"], expected["body"])
        self.assertEqual(effects[0]["source_ids"], expected["source_ids"])
        self.assertEqual(effects[0]["action_key"], row["payload"]["action_key"])
        self.assertEqual(effects[0]["stamp"], "review-session")
        self.assertEqual(effects[0]["status"], "pending")
        self.assertFalse([m for m in channel.messages("SYN-Q-deadline") if not m.from_outside])
        event = next(e for e in runtime.trace("review-session").lines() if e["type"] == "approval_decision")
        self.assertEqual(event["screen"], item["screen"])
        self.assertEqual(event["decided_by"], "operator")
        self.assertGreaterEqual(event["elapsed_s"], 0)

    def test_deny_then_approve_cannot_execute_and_duplicate_decision_does_not_repeat(self):
        item = self.request()
        self.assertIn("Denied", self.decide(item, False).text)
        self.assertIn("already denied", self.decide(item).text)
        self.assertFalse(course.effects())
        seed.reset()
        seed.seed(None)
        item = self.request()
        self.decide(item)
        self.assertIn("already executed", self.decide(item).text)
        self.assertEqual(len(course.effects()), 1)

    def test_approval_after_restart_executes_in_original_session(self):
        item = self.request()
        script = """from agent import service
from harness import runtime, turns
runtime.configure(backend='tests.fakes:GoodAgent')
item=service.pending_approvals()[0]
reply=turns.decide_approval(item['id'],True,'after restart',session_id=item['session_id'])
print(reply.text)
"""
        completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
        self.assertIn("saved reply", completed.stdout)
        self.assertEqual(len(course.effects()), 1)
        self.assertEqual(course.effects()[0]["stamp"], item["session_id"])
        self.assertEqual(approvals.get(item["id"])["status"], "executed")

    def test_changed_source_blocks_stale_review(self):
        item = self.request()
        doc = course.record("document", "SYN-DOC-deadline")
        course.put_record("document", {**doc, "version": "changed-after-review"})
        reply = self.decide(item)
        self.assertIn("changed", reply.text)
        self.assertFalse(course.effects())
        self.assertEqual(approvals.get(item["id"])["status"], "blocked")
        self.assertTrue(any(r["id"] == item["id"] for r in queue.waiting()))

    def test_new_prohibition_or_stop_blocks_previously_reviewed_call(self):
        for reason in ("deny", "stop"):
            with self.subTest(reason=reason):
                seed.reset()
                seed.seed(None)
                item = self.request()
                if reason == "deny":
                    state.set_limit("review-session", "drafts", "deny", "operator changed rule")
                else:
                    state.set_stopped("review-session", True)
                self.decide(item)
                self.assertFalse(course.effects())
                self.assertEqual(approvals.get(item["id"])["status"], "blocked")

    def test_changed_question_to_staff_only_cannot_be_approved(self):
        item = self.request()
        q = course.record("question", "SYN-Q-deadline")
        course.put_record("question", {**q, "kind": "personal"})
        self.decide(item)
        self.assertFalse(course.effects())

    def test_outside_approval_and_another_console_task_do_not_release_hold(self):
        item = self.request()
        turns.outside_reply("SYN-Q-deadline", "approved", sender="student")
        reply = turns.operator_turn("review-session", "Process SYN-Q-office")
        self.assertIn("saved as queue", reply.text)
        self.assertFalse(course.effects())
        self.assertEqual(service.pending_approvals()[0]["id"], item["id"])

    def test_untrusted_text_is_escaped_in_actual_screen(self):
        channel.receive("SYN-Q-deadline", "<script>alert('approved')</script>", sender="student")
        item = self.request()
        with TestClient(app) as client:
            page = client.get("/approvals").text
            self.assertIn("outside text, untrusted", page)
            self.assertNotIn("<script>alert('approved')</script>", page)
            response = client.post("/approvals", data={"approval_id": item["id"], "decision": "approve"})
            self.assertIn("saved reply", response.text)
        self.assertEqual(len(course.effects()), 1)

    def test_concurrent_decisions_execute_once(self):
        item = self.request()
        with ThreadPoolExecutor(max_workers=2) as pool:
            replies = list(pool.map(lambda _: self.decide(item), range(2)))
        self.assertEqual(len(course.effects()), 1)
        self.assertEqual(approvals.get(item["id"])["status"], "executed")
        self.assertEqual(sum("saved reply" in r.text for r in replies), 1)

    def test_tampered_arguments_or_unclaimed_approval_do_not_authorize(self):
        item = self.request()
        row = approvals.get(item["id"])
        p = row["payload"]
        reg = Registry("review-session", p["allowed_questions"], approval_id=item["id"])
        reg.read_questions.update(p["read_questions"])
        reg.read_docs.update(p["read_documents"])
        # Knowing a pending ID is not an operator decision.
        self.assertTrue(reg.call(p["tool"], p["arguments"]).is_error)
        approvals.claim(item["id"], True, "test trusted decision")
        changed = {**p["arguments"], "body": "Different text never shown to reviewer"}
        self.assertTrue(reg.call(p["tool"], changed).is_error)
        self.assertFalse(course.effects())

    def test_inflight_or_unknown_outcome_is_held_not_blindly_repeated(self):
        item = self.request()
        # Simulate process death after a decision was claimed. No replay is guessed.
        approvals.claim(item["id"], True, "claimed before crash")
        self.assertIn("already executing", self.decide(item).text)
        self.assertFalse(course.effects())
        self.assertTrue(any(r["id"] == item["id"] and r["status"] == "executing" for r in queue.waiting()))

    def test_revalidated_hook_error_denies_approved_operation(self):
        item = self.request()
        with mock.patch("policy.hook.load_policy", side_effect=OSError("policy missing")):
            reply = self.decide(item)
        self.assertIn("did not complete", reply.text)
        self.assertFalse(course.effects())

    def test_repeated_same_request_has_one_pending_review(self):
        turns.operator_turn("review-session", "/limit drafts approval")
        registry = Registry("review-session", ["SYN-Q-deadline"])
        registry.call("course_get_question", {"question_id": "SYN-Q-deadline"})
        registry.call("course_read_document", {"document_id": "SYN-DOC-deadline"})
        args = {"question_id": "SYN-Q-deadline", "body": course.record("document", "SYN-DOC-deadline")["answer"],
                "source_ids": ["SYN-DOC-deadline"]}
        a = registry.call("course_create_reply", args)
        b = registry.call("course_create_reply", args)
        self.assertEqual(a.data["approval_id"], b.data["approval_id"])
        self.assertEqual(len(service.pending_approvals()), 1)
        self.assertFalse(course.effects())

    def test_scripted_task_uses_same_gate_and_independent_check(self):
        record = self.run_task("tasks/dev/approval_draft.yaml", "approval-test", backend="tests.fakes:GoodAgent")
        self.assertTrue(record["passed"], record)
        self.assertEqual(record["measures"]["approved_exact_actions"], 1)
        self.assertEqual(record["approvals"]["answered"], 1)

    def test_registry_cannot_continue_run_while_approval_waits(self):
        self.request()
        registry = Registry("review-session", ["SYN-Q-deadline"])
        result = registry.call("course_search_materials", {"query": "deadline"})
        self.assertTrue(result.is_error)
        self.assertFalse(course.effects())
