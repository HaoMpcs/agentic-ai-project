"""Disclosed sends: final-screen review, denied bypasses and target receipts."""
from __future__ import annotations

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
from policy import approvals, disclosure, escalations, state
from sandbox import course, seed
from tests.support import ScratchTest


class DisclosureTests(ScratchTest):
    def setUp(self):
        super().setUp()
        seed.reset()
        seed.seed(None)
        runtime.configure(backend="tests.fakes:GoodAgent")

    def draft(self):
        turns.operator_turn("send-review", "Process SYN-Q-deadline")
        return course.effects()[0]

    def pending_send(self):
        draft = self.draft()
        reply = turns.operator_turn("send-review", f"/send {draft['id']}")
        self.assertIn("Approvals", reply.text)
        item = service.pending_approvals()[0]
        self.assertFalse(self.sent())
        return draft, item

    def sent(self):
        return [m for m in channel.messages("SYN-Q-deadline") if m.sender == channel.AGENT]

    def approve(self, item, decision=True):
        return turns.decide_approval(item["id"], decision, session_id=item["session_id"])

    def test_builder_is_code_owned_idempotent_and_rejects_embedded_line(self):
        text = disclosure.render("Public answer")
        self.assertEqual(disclosure.render(text), text)
        self.assertTrue(disclosure.valid(text))
        self.assertEqual(text.count(disclosure.LINE), 1)
        with self.assertRaises(ValueError):
            disclosure.render(disclosure.LINE + "\nMisplaced")

    def test_gate_shows_and_sends_exact_final_disclosed_message(self):
        draft, item = self.pending_send()
        final = disclosure.render(draft["body"])
        self.assertEqual(item["screen"]["effect"]["arguments"]["body"], final)
        self.assertTrue(item["screen"]["effect"]["publishes_to_student"])
        self.assertEqual(item["screen"]["facts"]["external_recipients"], 1)
        with TestClient(app) as client:
            page = client.get("/approvals").text
            self.assertIn("cannot be recalled", page)
            self.assertIn(disclosure.LINE, page)
        reply = self.approve(item)
        self.assertIn("sent to", reply.text)
        self.assertEqual([m.text for m in self.sent()], [final])
        self.assertEqual(course.effect(draft["id"])["status"], "sent")
        self.assertEqual(approvals.get(item["id"])["status"], "executed")

    def test_direct_registry_send_without_line_denied_before_approval_and_write(self):
        draft = self.draft()
        registry = Registry("probe", [draft["question_id"]], send_effect_ids=[draft["id"]])
        registry.call("course_get_question", {"question_id": draft["question_id"]})
        registry.call("course_read_document", {"document_id": "SYN-DOC-deadline"})
        args = {"question_id": draft["question_id"], "effect_id": draft["id"], "body": draft["body"]}
        before = course.effect(draft["id"])
        result = registry.call("course_send_reply", args)
        self.assertTrue(result.is_error)
        self.assertFalse(service.pending_approvals())
        self.assertEqual(course.effect(draft["id"]), before)
        self.assertFalse(self.sent())
        self.assertTrue(any(e.get("action_class") == "course_send_reply/missing_disclosure" for e in registry.trace.lines()))

    def test_valid_footer_does_not_grant_an_unselected_send_capability(self):
        draft = self.draft()
        registry = Registry("unselected", [draft["question_id"]])
        registry.call("course_get_question", {"question_id": draft["question_id"]})
        result = registry.call("course_send_reply", disclosure.prepare(draft["id"]))
        self.assertTrue(result.is_error)
        self.assertFalse(self.sent())
        self.assertFalse(any(d["name"] == "course_send_reply" for d in registry.definitions()))

    def test_deny_duplicate_and_concurrent_approval_cannot_duplicate_message(self):
        draft, item = self.pending_send()
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: self.approve(item), range(2)))
        self.approve(item)
        self.assertEqual(len(self.sent()), 1)
        seed.reset()
        seed.seed(None)
        draft, item = self.pending_send()
        self.approve(item, False)
        self.approve(item)
        self.assertFalse(self.sent())
        self.assertEqual(course.effect(draft["id"])["status"], "pending")

    def test_changed_source_or_send_limit_blocks_reviewed_send(self):
        for change in ("source", "limit"):
            with self.subTest(change=change):
                seed.reset()
                seed.seed(None)
                _, item = self.pending_send()
                if change == "source":
                    doc = course.record("document", "SYN-DOC-deadline")
                    course.put_record("document", {**doc, "version": "new-version"})
                else:
                    state.set_limit("send-review", "sends", "deny", "operator")
                self.approve(item)
                self.assertFalse(self.sent())

    def test_human_send_is_unchanged_but_auto_draft_cannot_bypass_gate(self):
        draft = self.draft()
        with self.assertRaisesRegex(ValueError, "automated"):
            course.send_pending(draft["id"])
        with TestClient(app) as client:
            response = client.post("/course/send", data={"effect_id": draft["id"], "reviewed": "yes"})
            self.assertIn("automated", response.text)
        self.assertFalse(self.sent())
        human = course.manual_draft("SYN-Q-concept", "My own human reply", [])
        course.send_pending(human["id"])
        human_messages = [m for m in channel.messages("SYN-Q-concept") if m.sender == channel.OPERATOR]
        self.assertEqual([m.text for m in human_messages], ["My own human reply"])

    def test_target_accepts_key_once_and_refuses_changed_content(self):
        body = disclosure.render("Target contract fixture")
        a = channel.send_once("SYN-Q-deadline", body, key="target-key")
        b = channel.send_once("SYN-Q-deadline", body, key="target-key")
        self.assertEqual(a.id, b.id)
        with self.assertRaises(ValueError):
            channel.send_once("SYN-Q-deadline", disclosure.render("Changed"), key="target-key")
        self.assertEqual(len(self.sent()), 1)

    def test_lost_target_response_escalates_then_confirms_without_resend(self):
        draft, item = self.pending_send()
        original = channel.send_once

        def committed_timeout(*args, **kwargs):
            original(*args, **kwargs)
            raise TimeoutError("response lost after commit")

        with mock.patch("channel.send_once", committed_timeout):
            self.approve(item)
        self.assertEqual(len(self.sent()), 1)
        self.assertEqual(course.effect(draft["id"])["status"], "uncertain")
        hold = escalations.records()[0]
        reply = turns.operator_turn("later-TA", f"/resolve {hold['id']} confirm")
        self.assertIn("Confirmed", reply.text)
        self.assertEqual(course.effect(draft["id"])["status"], "sent")
        self.assertEqual(len(self.sent()), 1)

    def test_absent_send_stays_held_no_blind_retry(self):
        draft, item = self.pending_send()
        with mock.patch("channel.send_once", side_effect=TimeoutError("before commit")) as send:
            self.approve(item)
        self.assertEqual(send.call_count, 1)
        hold = escalations.records()[0]
        turns.operator_turn("later-TA", f"/resolve {hold['id']} confirm")
        self.assertEqual(escalations.get(hold["id"])["status"], "awaiting_recovery")
        self.assertFalse(self.sent())

    def test_send_review_survives_new_process(self):
        _, item = self.pending_send()
        script = """from harness import runtime,turns
from agent import service
runtime.configure(backend='tests.fakes:GoodAgent')
item=service.pending_approvals()[0]
print(turns.decide_approval(item['id'],True,session_id=item['session_id']).text)
"""
        done = subprocess.run([sys.executable, "-c", script], check=True, text=True, capture_output=True)
        self.assertIn("sent to", done.stdout)
        self.assertEqual(len(self.sent()), 1)

    def test_stop_withdraws_send_and_resume_requires_new_review(self):
        _, item = self.pending_send()
        turns.operator_turn("send-review", "/stop")
        self.assertFalse(service.pending_approvals())
        self.approve(item)
        self.assertFalse(self.sent())
        turns.operator_turn("send-review", "/resume")
        new = service.pending_approvals()[0]
        self.approve(new)
        self.assertEqual(len(self.sent()), 1)

    def test_rollback_sent_run_explicitly_reports_no_compensation(self):
        draft, item = self.pending_send()
        self.approve(item)
        reply = turns.operator_turn("send-review", "/rollback " + item["run_id"])
        self.assertIn(draft["id"] + ": none", reply.text)
        self.assertEqual(course.effect(draft["id"])["status"], "sent")
        self.assertEqual(len(self.sent()), 1)

    def test_unsupported_private_draft_is_not_offered_for_send(self):
        draft = course.create_effect("reply", "SYN-Q-deadline", body="SYN-PRIVATE-CANARY-1", source_ids=[], key="bad-draft")
        reply = turns.operator_turn("bad-send", f"/send {draft['id']}")
        self.assertIn("cannot be sent", reply.text)
        self.assertFalse(service.pending_approvals())
        self.assertFalse(self.sent())

    def test_task_check_rejects_planted_undisclosed_agent_message(self):
        from tests.support import fixed_run, check_run
        task = "tasks/deadline_question.yaml"
        with fixed_run(task, "bad-disclosure", backend="tests.fakes:GoodAgent"):
            turns.operator_turn("bad-disclosure", "Process SYN-Q-deadline")
            channel.send("SYN-Q-deadline", "Unlabelled planted output")
            result = check_run(task, "bad-disclosure")
            self.assertFalse(result["passed"])
            self.assertIn("disclosure", result["reason"])

    def test_scripted_send_task_uses_real_gate_and_independent_check(self):
        record = self.run_task("tasks/dev/disclosed_send.yaml", "disclosed-send-test", backend="tests.fakes:GoodAgent")
        self.assertTrue(record["passed"], record)
        self.assertEqual(record["measures"]["disclosed_agent_messages"], 1)
