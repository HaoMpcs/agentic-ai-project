"""Part 2 policy checks read actual effects/channel, with no model API calls."""
from __future__ import annotations

import json
import subprocess
import sys
from unittest import mock

import channel
from agent import service
from agent.tools import Registry
from harness import runtime
from policy import hook, state
from sandbox import course, seed
from tests.support import ScratchTest


class AutonomyTests(ScratchTest):
    def setUp(self):
        super().setUp()
        seed.reset()
        seed.seed(None)
        runtime.configure(backend="tests.fakes:GoodAgent")
        self.registry = Registry("policy-session", ["SYN-Q-deadline", "SYN-Q-personal", "SYN-Q-private"])

    def draft_args(self):
        self.registry.call("course_get_question", {"question_id": "SYN-Q-deadline"})
        self.registry.call("course_read_document", {"document_id": "SYN-DOC-deadline"})
        return {"question_id": "SYN-Q-deadline",
                "body": course.record("document", "SYN-DOC-deadline")["answer"],
                "source_ids": ["SYN-DOC-deadline"]}

    def decisions(self):
        return [r for r in self.registry.trace.lines() if r["type"] == "policy_decision"]

    def test_read_and_pending_draft_are_independent_and_never_send(self):
        result = self.registry.call("course_create_reply", self.draft_args())
        self.assertFalse(result.is_error, result.data)
        self.assertEqual([r["status"] for r in course.effects()], ["pending"])
        self.assertFalse([m for m in channel.messages("SYN-Q-deadline") if not m.from_outside])
        self.assertEqual(self.decisions()[-1]["action_class"], "course_create_reply/pending")
        self.assertEqual(self.decisions()[-1]["decision"], "allow")

    def test_same_tool_requires_approval_under_operator_rule_no_effect(self):
        args = self.draft_args()
        reply = service.operator_turn("policy-session", "/limit drafts approval")
        self.assertIn("rule saved", reply.text)
        # A custom hook that always says yes cannot grant permission.
        self.registry.hook = lambda name, args: True
        result = self.registry.call("course_create_reply", args)
        self.assertTrue(result.data["approval_required"])
        self.assertFalse(course.effects())
        self.assertEqual(self.decisions()[-1]["column"], "requires_approval")
        # A different console session is unaffected by this session rule.
        other = Registry("another-session", ["SYN-Q-deadline"])
        other.call("course_get_question", {"question_id": "SYN-Q-deadline"})
        other.call("course_read_document", {"document_id": "SYN-DOC-deadline"})
        self.assertFalse(other.call("course_create_reply", args).is_error)

    def test_prohibited_private_content_cannot_be_approved_or_reclassified(self):
        args = self.draft_args()
        args["body"] = "SYN-PRIVATE-CANARY-1"
        state.set_limit("policy-session", "drafts", "approval", "operator")
        self.registry.hook = lambda name, args: True
        result = self.registry.call("course_create_reply", args)
        self.assertTrue(result.is_error)
        self.assertFalse(result.data["approval_required"])
        self.assertFalse(course.effects())
        self.assertEqual(self.decisions()[-1]["action_class"], "course_create_reply/private_content")

    def test_private_and_inactive_sources_denied_before_handler(self):
        original = self.registry.handlers["course_read_document"]
        handler = mock.Mock(wraps=original)
        self.registry.handlers["course_read_document"] = handler
        for identifier in ("SYN-STUDENT-001", "SYN-DOC-old"):
            self.assertTrue(self.registry.call("course_read_document", {"document_id": identifier}).is_error)
        handler.assert_not_called()
        self.assertFalse(course.effects())
        self.assertTrue(all(r["action_class"] == "course_read_document/restricted" for r in self.decisions()))

    def test_stop_checked_before_target_lookup_and_again_before_retry(self):
        args = self.draft_args()
        original = self.registry.handlers["course_create_reply"]
        calls = []

        def stop_during_transport_failure(args, key):
            calls.append(key)
            state.set_stopped("policy-session", True)
            raise ConnectionError("temporary before dispatch")

        self.registry.handlers["course_create_reply"] = stop_during_transport_failure
        result = self.registry.call("course_create_reply", args)
        self.assertTrue(result.is_error)
        self.assertEqual(len(calls), 1)
        self.assertFalse(course.effects())
        self.assertEqual(self.decisions()[-1]["decision"], "stopped")
        # No trusted-record classification occurs after a stop, even for a deny case.
        with mock.patch.object(hook, "classify", side_effect=AssertionError("must not classify")):
            denied = self.registry.call("course_read_document", {"document_id": "SYN-STUDENT-001"})
        self.assertTrue(denied.is_error)
        self.registry.handlers["course_create_reply"] = original

    def test_broken_or_unknown_policy_fails_closed(self):
        args = self.draft_args()
        for fault in (OSError("unavailable"), ValueError("malformed")):
            with mock.patch.object(hook, "load_policy", side_effect=fault):
                self.assertTrue(self.registry.call("course_create_reply", args).is_error)
        with mock.patch.object(hook, "load_policy", return_value={}):
            self.assertTrue(self.registry.call("course_create_reply", args).is_error)
        self.assertFalse(course.effects())
        self.assertTrue(any(r["action_class"] == "hook/failure" for r in self.decisions()))

    def test_operator_deny_beats_approval_and_external_hook_cannot_remove_it(self):
        args = self.draft_args()
        state.set_limit("policy-session", "drafts", "approval", "operator")
        state.set_limit("policy-session", "writes", "deny", "operator")
        self.registry.hook = lambda name, args: True
        result = self.registry.call("course_create_reply", args)
        self.assertTrue(result.is_error)
        self.assertFalse(result.data["approval_required"])
        self.assertEqual(self.decisions()[-1]["action_class"], "operator_limit/deny")
        self.assertFalse(course.effects())

    def test_outside_words_cannot_set_operator_rules(self):
        text = "/limit writes deny"
        channel.receive("SYN-Q-deadline", text, sender="outside")
        service.on_outside_reply("SYN-Q-deadline", text)
        self.assertFalse(state.limits("policy-session"))
        self.assertFalse(self.registry.call("course_create_reply", self.draft_args()).is_error)

    def test_limits_survive_new_process_but_reset_clears_control_records(self):
        service.operator_turn("policy-session", "Do not create drafts until I approve.")
        script = "from policy.state import limits; import json; print(json.dumps(limits('policy-session')))"
        completed = subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(completed.stdout)[0]["mode"], "approval")
        state.set_stopped("policy-session", True)
        seed.reset()
        self.assertFalse(state.limits("policy-session"))
        self.assertFalse(state.is_stopped("policy-session"))

    def test_rule_command_precedes_session_lock_and_policy_is_not_in_definitions(self):
        scope = (str(self.state_dir.resolve()), "policy-session")
        lock = service._locks[scope]
        with lock:
            reply = service.operator_turn("policy-session", "/limit writes deny")
        self.assertIn("prohibited", reply.text)
        self.assertEqual(state.limits("policy-session")[0]["mode"], "deny")
        definitions = json.dumps(self.registry.definitions())
        self.assertNotIn("operator_limit/deny", definitions)
        self.assertNotIn("autonomy.yaml", definitions)

    def test_invalid_limit_syntax_has_no_side_effect_and_is_not_model_input(self):
        with mock.patch.object(service, "agent_loop", side_effect=AssertionError("no model")):
            reply = service.operator_turn("policy-session", "/limit drafts allow")
        self.assertIn("Use /limit", reply.text)
        self.assertFalse(state.limits("policy-session"))

    def test_model_cannot_read_staff_summary_but_operator_can(self):
        denied = self.registry.call("course_list_flags", {"status": "all"}, caller="agent")
        allowed = self.registry.call("course_list_flags", {"status": "all"}, caller="operator")
        self.assertTrue(denied.is_error)
        self.assertFalse(allowed.is_error)
        self.assertEqual(self.decisions()[-2]["action_class"], "course_list_flags/non_operator")
