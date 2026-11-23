"""Contract, budget, trace and silent-divergence checks for m2-split."""
from __future__ import annotations

from agent import topology
from agent.tools import Registry
from harness import runtime
from sandbox import course, seed
from tests.support import ScratchTest


class TopologyTests(ScratchTest):
    def setUp(self):
        super().setUp()
        seed.reset()
        seed.seed(None)
        runtime.configure(backend="tests.fakes:GoodAgent", overrides=["topology=split"])

    def test_contract_break_is_rejected_and_role_trace_has_parent_and_spend(self):
        registry = Registry("split", ["SYN-Q-deadline"])
        def malformed(registry, ids, budget):
            return {"status": "found"}
        with self.assertRaisesRegex(ValueError, "Invalid role return"):
            topology.run_candidate(registry, ["SYN-Q-deadline"], runtime.trace("split"), roles=(malformed,))
        topology.run_candidate(registry, ["SYN-Q-deadline"], runtime.trace("split"), parent_id="parent")
        ends = [e for e in runtime.trace("split").lines() if e["type"] == "topology_agent_end"]
        self.assertEqual(len(ends), 2)
        self.assertTrue(all(e["parent_id"] == "parent" and "spent" in e for e in ends))

    def test_combined_check_catches_planted_silent_divergence(self):
        good = course.create_effect("flag", "SYN-Q-deadline", reason="missing_information", key="one")
        self.assertTrue(topology.combined_end_state(["SYN-Q-deadline"], [good])["passed"])
        duplicate = {**good, "id": "planted", "action_key": "two"}
        result = topology.combined_end_state(["SYN-Q-deadline"], [good, duplicate])
        self.assertFalse(result["passed"])
        self.assertIn("found 2", result["errors"][0])

    def test_roles_share_one_enforced_call_budget(self):
        registry = Registry("budget", ["SYN-Q-deadline"])
        budget = topology.SharedBudget(tool_calls=1)
        returns = topology.run_candidate(registry, ["SYN-Q-deadline"], runtime.trace("budget"), budget=budget)
        self.assertEqual(budget.tool_calls, 1)
        self.assertEqual(returns[1]["status"], "out of budget")

