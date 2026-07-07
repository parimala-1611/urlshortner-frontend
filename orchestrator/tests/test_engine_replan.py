import shutil
import unittest

from orchestrator.engine import Engine
from orchestrator.pipeline import Pipeline, Stage
from orchestrator.tests import fixture_stages
from orchestrator.tests.test_helpers import make_temp_git_repo


class EngineReplanTest(unittest.TestCase):
    def setUp(self):
        fixture_stages.reset_fixture_state()
        self.repo = make_temp_git_repo()
        self.run_dir = self.repo / "_run"

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_replan_reopens_earlier_stage_once_then_completes(self):
        pipeline = Pipeline(name="p", description="", stages=[
            Stage(name="a", runner="orchestrator.tests.fixture_stages.always_pass"),
            Stage(name="b", runner="orchestrator.tests.fixture_stages.always_pass", depends_on=["a"]),
            Stage(name="c", runner="orchestrator.tests.fixture_stages.replan_once_then_pass",
                  depends_on=["b"], params={"key": "replan-test-1", "replan_to": "a"}),
        ])
        engine = Engine(pipeline, "run-replan", self.run_dir, self.repo)
        terminal = engine.run()

        self.assertEqual(terminal, "completed")
        events = engine.audit.read_events()
        enter_events = [e["stage"] for e in events if e["event"] == "enter"]
        self.assertEqual(enter_events.count("a"), 2)
        self.assertEqual(enter_events.count("b"), 2)
        self.assertEqual(enter_events.count("c"), 2)
        self.assertTrue(any(e["event"] == "replan" for e in events))
        self.assertEqual(engine.status["c"].value, "passed")


if __name__ == "__main__":
    unittest.main()
