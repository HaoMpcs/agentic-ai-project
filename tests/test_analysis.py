from pathlib import Path
from experiments.analysis.summarize import summarize
from experiments.analysis.tool_overhead import schema_stats
from agent.tools import Registry
from harness import runtime
from tests.support import ScratchTest


class AnalysisTests(ScratchTest):
    def test_recomputes_workflow_and_agent_records_and_rejects_fake_evidence(self):
        first=self.run_task('tasks/deadline_question.yaml','analysis',backend='tests.fakes:GoodAgent')
        second=self.run_task('tasks/conceptual_question.yaml','analysis',backend='tests.fakes:GoodAgent')
        folder=self.tmp/'results/_free/analysis'
        with self.assertRaises(ValueError):summarize(folder)
        report=summarize(folder,include_free=True)
        self.assertEqual(report['runs'],2)
        self.assertEqual(report['passed'],2)
        self.assertEqual(report['tokens']['total'],first['tokens']['total']+second['tokens']['total'])
        self.assertEqual(report['cost_usd'],0)
        self.assertEqual(set(report['by_task']),{'deadline_question','conceptual_question'})
        self.assertEqual(report['events']['critique_pass'],2)

    def test_strict_schema_metrics(self):
        runtime.configure(backend='tests.fakes:GoodAgent',overrides=['strict.flag=on'])
        stats=schema_stats(Registry('schema',[]).definitions())
        self.assertEqual(stats,{'strict_tools':1,'optional_parameters':0,'union_typed_parameters':0,'deepest_schema_nesting':1})

    def test_recomputes_plan_outcomes_and_draft_checkpoint(self):
        self.run_task('tasks/batch_questions.yaml', 'plan-analysis', backend='tests.fakes:CorrectingPlanner',
                      overrides=['plan.batch=on'])
        report = summarize(self.tmp / 'results/_free/plan-analysis', include_free=True)
        self.assertEqual(report['passed'], 1)
        self.assertEqual(report['events']['plan_outcome_pass'], 12)
        self.assertEqual(report['events']['checkpoint_draft_supported_fail'], 1)
        self.assertEqual(report['events']['plan_revisions'], 1)
        self.assertEqual(report['events']['critique_fail'], 1)
        self.assertEqual(report['events']['plan_rejected_attempts'], 1)
