"""Part 2 durable holds: actual writes, silent operator, cap and later session."""
from __future__ import annotations

import json
import subprocess
import sys
from unittest import mock

from fastapi.testclient import TestClient

import channel
from agent import service
from agent.tools import Registry
from app.main import app
from harness import runtime, turns
from policy import approvals, escalations, state
from sandbox import course, queue, seed
from tests.support import ScratchTest


class EscalationTests(ScratchTest):
    def setUp(self):
        super().setUp()
        seed.reset()
        seed.seed(None)
        runtime.configure(backend="tests.fakes:GoodAgent")

    def fail_write(self, session="held-session", committed=False):
        registry = Registry(session, ["SYN-Q-deadline"])
        registry.call("course_get_question", {"question_id": "SYN-Q-deadline"})
        registry.call("course_read_document", {"document_id": "SYN-DOC-deadline"})
        args = {"question_id": "SYN-Q-deadline", "body": course.record("document", "SYN-DOC-deadline")["answer"],
                "source_ids": ["SYN-DOC-deadline"]}

        def uncertain(a, key):
            if committed:
                course.create_effect("reply", a["question_id"], body=a["body"], source_ids=a["source_ids"], key=key)
            raise TimeoutError("ambiguous transport")

        registry.handlers["course_create_reply"] = uncertain
        result = registry.call("course_create_reply", args)
        return registry, escalations.get(result.data["escalation_id"])

    def test_packet_has_three_fields_and_hold_denies_further_dispatch(self):
        registry, row = self.fail_write()
        self.assertEqual(row["status"], "held")
        self.assertEqual(row["payload"]["signal"], "write_outcome_unknown")
        self.assertTrue(all(row["payload"]["packet"].get(k) for k in ("attempted", "reason", "needed")))
        self.assertTrue(row["payload"]["action_key"])
        self.assertFalse(course.effects())
        handler = mock.Mock()
        registry.handlers["course_search_materials"] = handler
        self.assertTrue(registry.call("course_search_materials", {"query": "deadline"}).is_error)
        handler.assert_not_called()
        self.assertEqual(escalations.get(row["id"])["status"], "held")

    def test_silence_and_deadline_leave_held_with_no_write(self):
        _, row = self.fail_write()
        with mock.patch("policy.escalations.now", return_value="2099-01-01T00:00:00+00:00"):
            self.assertTrue(escalations.get(row["id"])["timed_out"])
            item = next(r for r in queue.waiting() if r["id"] == row["id"])
            self.assertTrue(item["timed_out"])
            self.assertEqual(item["status"], "held")
        self.assertFalse(course.effects())

    def test_confirm_in_new_process_and_new_session_reuses_existing_effect(self):
        _, row = self.fail_write(committed=True)
        self.assertEqual(len(course.effects()), 1)
        script = """from harness import runtime, turns
runtime.configure(backend='tests.fakes:GoodAgent')
import sys
print(turns.operator_turn('later-review-session','/resolve '+sys.argv[1]+' confirm').text)
"""
        completed = subprocess.run([sys.executable, "-c", script, row["id"]], check=True, capture_output=True, text=True)
        self.assertIn("Confirmed existing effect", completed.stdout)
        self.assertEqual(escalations.get(row["id"])["status"], "resolved")
        self.assertEqual(len(course.effects()), 1)
        self.assertFalse([x for x in queue.waiting() if x["id"] == row["id"]])
        self.assertIn("Already resolved", turns.operator_turn("later-review-session", f"/resolve {row['id']} confirm").text)
        self.assertEqual(len(course.effects()), 1)

    def test_absent_effect_is_handed_off_not_retried(self):
        _, row = self.fail_write()
        reply = turns.operator_turn("new-reviewer", f"/resolve {row['id']} confirm")
        self.assertIn("Part 1", reply.text)
        self.assertEqual(escalations.get(row["id"])["status"], "awaiting_recovery")
        self.assertFalse(course.effects())
        self.assertTrue(any(x["id"] == row["id"] for x in queue.waiting()))

    def test_unavailable_readback_never_releases_hold(self):
        _, row = self.fail_write()
        with mock.patch("policy.escalations.inspect", side_effect=OSError("unavailable")):
            reply = turns.operator_turn("new-reviewer", f"/resolve {row['id']} confirm")
        self.assertIn("remains held", reply.text)
        self.assertEqual(escalations.get(row["id"])["status"], "held")
        self.assertFalse(course.effects())

    def test_mismatched_key_content_cannot_be_confirmed(self):
        _, row = self.fail_write()
        course.create_effect("reply", "SYN-Q-deadline", body="Different content", source_ids=[], key=row["payload"]["action_key"])
        reply = turns.operator_turn("new-reviewer", f"/resolve {row['id']} confirm")
        self.assertIn("different content", reply.text)
        self.assertEqual(escalations.get(row["id"])["status"], "held")
        self.assertEqual(len(course.effects()), 1)

    def test_cap_suppresses_packet_but_queue_and_explicit_inspection_work(self):
        settings = {"daily_cap": 0, "hold_timeout_seconds": 86400, "timezone": "America/New_York"}
        with mock.patch("policy.escalations.config", return_value=settings):
            registry, row = self.fail_write()
        self.assertTrue(row["over_cap"])
        self.assertFalse(any(x["type"] == "escalation_packet" for x in registry.trace.lines()))
        item = next(x for x in queue.waiting() if x["id"] == row["id"])
        self.assertTrue(item["over_cap"])
        reply = turns.operator_turn("new-reviewer", "/escalations")
        self.assertIn("attempted:", reply.text)
        self.assertIn(row["id"], reply.text)
        self.assertFalse(course.effects())

    def test_approval_requests_count_against_shared_daily_cap(self):
        turns.operator_turn("review", "/limit drafts approval")
        turns.operator_turn("review", "Process SYN-Q-deadline")
        self.assertEqual(len(approvals.records()), 1)
        settings = {"daily_cap": 1, "hold_timeout_seconds": 86400, "timezone": "America/New_York"}
        with mock.patch("policy.escalations.config", return_value=settings):
            _, row = self.fail_write(session="other-run")
        self.assertTrue(row["over_cap"])

    def test_outside_approved_or_confirm_text_cannot_resolve(self):
        _, row = self.fail_write(committed=True)
        turns.outside_reply("SYN-Q-deadline", f"/resolve {row['id']} confirm", sender="student")
        self.assertEqual(escalations.get(row["id"])["status"], "held")
        self.assertEqual(len(course.effects()), 1)

    def test_console_and_queue_show_hold_and_same_session_cannot_start_work(self):
        _, row = self.fail_write()
        reply = turns.operator_turn("held-session", "Process SYN-Q-deadline")
        self.assertIn("held for TA", reply.text)
        with TestClient(app) as client:
            self.assertIn(row["id"], client.get("/queue").text)
            response = client.post("/console/reviewer/turn", data={"text": "/escalations"})
            self.assertEqual(response.status_code, 200)
        self.assertFalse(course.effects())

    def test_stop_prevents_confirmation_and_reset_clears_holds(self):
        _, row = self.fail_write(committed=True)
        state.set_stopped("held-session", True)
        reply = turns.operator_turn("new-reviewer", f"/resolve {row['id']} confirm")
        self.assertIn("stopped", reply.text)
        self.assertEqual(escalations.get(row["id"])["status"], "held")
        seed.reset()
        self.assertEqual(escalations.records(), [])

    def test_read_timeout_and_semantic_error_do_not_trigger_write_signal(self):
        registry = Registry("reads", ["SYN-Q-deadline"])
        registry.handlers["course_search_materials"] = mock.Mock(side_effect=TimeoutError())
        registry.call("course_search_materials", {"query": "deadline"})
        registry.call("course_search_materials", {"query": ""})
        self.assertFalse(escalations.records())

    def test_workflow_surfaces_packet_and_stops_without_following_operations(self):
        with mock.patch.object(Registry, "_reply", side_effect=TimeoutError("before commit")):
            reply = turns.operator_turn("workflow-held", "Process SYN-Q-deadline")
        self.assertIn("attempted:", reply.text)
        self.assertIn("needed:", reply.text)
        self.assertFalse(course.effects())
        self.assertEqual(len(escalations.records()), 1)
        self.assertTrue(any(e.get("terminal_reason") == "escalated_held"
                            for e in runtime.trace("workflow-held").lines()))

    def test_confirming_approved_committed_write_settles_uncertain_gate(self):
        turns.operator_turn("review", "/limit drafts approval")
        turns.operator_turn("review", "Process SYN-Q-deadline")
        item = service.pending_approvals()[0]
        with mock.patch.object(Registry, "_verify_effect", side_effect=TimeoutError("readback failed")):
            turns.decide_approval(item["id"], True, session_id="review")
        self.assertEqual(approvals.get(item["id"])["status"], "uncertain")
        row = escalations.records()[0]
        self.assertEqual(len(course.effects()), 1)
        reply = turns.operator_turn("later-reviewer", f"/resolve {row['id']} confirm")
        self.assertIn("Confirmed existing effect", reply.text)
        self.assertEqual(approvals.get(item["id"])["status"], "executed")
        self.assertFalse(escalations.records())
        self.assertEqual(len(course.effects()), 1)
