"""Plan postconditions and bounded, pre-write draft revisions."""
from __future__ import annotations

import copy
import json
from unittest import mock

import channel
from agent.planning import validate
from agent.tools import Registry
from harness.trace import read_trace
from sandbox import course
from tests.fakes import CorrectingPlanner, valid_plan
from tests.support import ScratchTest


class PlanningTests(ScratchTest):
    def run_batch(self, backend="CorrectingPlanner"):
        return self.run_task("tasks/batch_questions.yaml", "planning", backend="tests.fakes:" + backend)

    def trace(self, record):
        return read_trace(next(self.tmp.rglob(record["run_id"] + ".trace.jsonl")))

    def test_unknown_outcome_rejected_before_execution(self):
        record = self.run_batch("WrongOutcomePlanner")
        self.assertFalse(record["passed"])
        self.assertIn("plan_rejected", record["end_reasons"])
        self.assertFalse(any(c["plan_step"] for c in record["tool_calls"]))
        self.assertFalse(course.effects())

    def test_outcome_must_belong_to_its_tool(self):
        plan = valid_plan([{"id": "SYN-Q-deadline", "topic": "deadline"}])
        plan["steps"][0]["expected"] = "reply_pending"
        self.assertTrue(any("requires expected=question_read" in error
                            for error in validate(plan, ["SYN-Q-deadline"])))

    def test_shape_valid_but_wrong_results_halt_before_next_step(self):
        cases = [("_question", "question", "id", "SYN-Q-other", 0),
                 ("_document", "document", "active", False, 0),
                 ("_reply", "effect", "status", "sent", 1)]
        for method, container, field, value, persisted in cases:
            with self.subTest(method=method):
                original = getattr(Registry, method)

                def wrong_result(registry, arguments, key):
                    output = original(registry, arguments, key)
                    output[container][field] = value
                    return output

                with mock.patch.object(Registry, method, wrong_result):
                    record = self.run_batch("GoodAgent")
                self.assertFalse(record["passed"])
                self.assertIn("plan_outcome_mismatch", record["end_reasons"])
                failures = [e for e in self.trace(record) if e["type"] == "plan_outcome" and not e["passed"]]
                self.assertEqual(len(failures), 1)
                # A failed postcondition after a write cannot undo that write.
                self.assertEqual(len(course.effects()), persisted)
                self.assertTrue(all(e["question_id"] == "SYN-Q-deadline" for e in course.effects()))

    def test_draft_revision_preserves_prefix_and_persists_once(self):
        contexts = []
        original = CorrectingPlanner.plan

        def observe(planner, context):
            contexts.append(copy.deepcopy(context))
            return original(planner, context)

        with mock.patch.object(CorrectingPlanner, "plan", observe):
            record = self.run_batch()
        self.assertTrue(record["passed"], record)
        self.assertIn("plan_completed", record["end_reasons"])
        events = self.trace(record)
        plans = [e for e in events if e["type"] == "plan"]
        self.assertEqual([p["version"] for p in plans], [1, 2])
        self.assertEqual(plans[0]["plan"]["steps"][:3], plans[1]["plan"]["steps"][:3])
        reviews = [e for e in events if e["type"] == "draft_critique" and e["question_id"] == "SYN-Q-deadline"]
        self.assertEqual([e["passed"] for e in reviews], [False, True])
        replies = [c for c in record["tool_calls"] if c["name"] == "course_create_reply"
                   and c["input"]["question_id"] == "SYN-Q-deadline"]
        self.assertEqual(len({c["idempotency_key"] for c in replies}), 1)
        self.assertEqual(len(course.effects()), 3)
        self.assertTrue(all(e["status"] == "pending" for e in course.effects()))
        self.assertTrue(all(m.from_outside for t in channel.threads() for m in channel.messages(t["thread_id"])))
        revised = contexts[1]
        self.assertEqual(revised["checkpoint"]["name"], "draft_supported")
        serialized = json.dumps(revised)
        self.assertNotIn("untrusted_messages", serialized)
        self.assertNotIn("When is Assignment 2 due?", serialized)
        self.assertNotIn("SYN-PRIVATE-", serialized)
        self.assertNotIn(course.record("document", "SYN-DOC-deadline")["answer"], serialized)
        diff = next(e for e in events if e["type"] == "plan_execution_diff")
        self.assertTrue(diff["aligned"])
        self.assertEqual(diff["skipped"], [])
        self.assertEqual(diff["rejected"], ["q0_reply"])

    def test_replaced_rejected_step_is_not_an_extra_call(self):
        record = self.run_batch("RenamingCorrectingPlanner")
        self.assertTrue(record["passed"], record)
        diff = next(e for e in self.trace(record) if e["type"] == "plan_execution_diff")
        self.assertEqual(diff["rejected"], ["q0_reply"])
        self.assertEqual(diff["extra"], [])
        self.assertEqual(diff["out_of_order"], [])
        self.assertEqual(diff["skipped"], [])
        self.assertIn("repaired_reply", diff["executed"])

    def test_repeated_bad_draft_stops_at_shared_revision_limit(self):
        record = self.run_batch("NeverCorrectPlanner")
        self.assertFalse(record["passed"])
        self.assertIn("revision_limit", record["end_reasons"])
        self.assertEqual(len([e for e in self.trace(record) if e["type"] == "draft_critique"]), 2)
        self.assertFalse(course.effects())

    def test_later_draft_revision_preserves_completed_write(self):
        record = self.run_batch("LateCorrectingPlanner")
        self.assertTrue(record["passed"], record)
        plans = [e for e in self.trace(record) if e["type"] == "plan"]
        self.assertEqual(plans[0]["plan"]["steps"][:7], plans[1]["plan"]["steps"][:7])
        first_writes = [c for c in record["tool_calls"] if c["name"] == "course_create_reply"
                        and c["input"]["question_id"] == "SYN-Q-deadline"]
        self.assertEqual(len(first_writes), 1)
        self.assertEqual(len(course.effects()), 3)

    def test_source_and_draft_checkpoints_share_revision_budget(self):
        record = self.run_task("tasks/dev/checkpoint_revision.yaml", "shared-budget",
                               backend="tests.fakes:MixedCheckpointPlanner")
        self.assertIn("revision_limit", record["end_reasons"])
        events = self.trace(record)
        self.assertEqual(len([e for e in events if e["type"] == "plan"]), 2)
        self.assertEqual([e["name"] for e in events if e["type"] == "plan_checkpoint" and not e["passed"]],
                         ["sources_available", "draft_supported"])
        self.assertEqual(len(course.effects()), 1)
        self.assertEqual(course.effects()[0]["kind"], "flag")

    def test_critique_limit_still_applies_with_more_revision_budget(self):
        with mock.patch("agent.planning.MAX_REVISIONS", 5):
            record = self.run_batch("NeverCorrectPlanner")
        self.assertIn("critique_limit", record["end_reasons"])
        self.assertEqual(len([e for e in self.trace(record) if e["type"] == "draft_critique"]), 3)
        self.assertFalse(course.effects())

    def test_invalid_draft_revision_never_runs(self):
        for backend in ("BadDraftRevision", "MalformedDraftRevision"):
            with self.subTest(backend=backend):
                record = self.run_batch(backend)
                self.assertIn("revision_rejected", record["end_reasons"])
                self.assertFalse(record["passed"])
                self.assertEqual(len([c for c in record["tool_calls"] if c["plan_step"]]), 4)
                self.assertFalse(course.effects())

    def test_generic_error_is_not_a_draft_checkpoint(self):
        with mock.patch.object(Registry, "_reply", side_effect=ValueError("Revise draft. Generic tool error.")):
            record = self.run_batch("GoodAgent")
        self.assertIn("plan_tool_error", record["end_reasons"])
        self.assertEqual(len([e for e in self.trace(record) if e["type"] == "plan"]), 1)
        self.assertFalse(course.effects())

    def test_uncertain_write_never_revises_or_retries(self):
        with mock.patch.object(Registry, "_verify_effect", side_effect=TimeoutError("Uncertain read-back")):
            record = self.run_batch("GoodAgent")
        self.assertIn("ambiguous_tool", record["end_reasons"])
        self.assertFalse(record["passed"])
        self.assertEqual(len([c for c in record["tool_calls"] if c["name"] == "course_create_reply"]), 1)
        self.assertEqual(len([e for e in self.trace(record) if e["type"] == "plan"]), 1)
        self.assertEqual(len(course.effects()), 1)
