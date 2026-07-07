import shutil
import unittest

from orchestrator.engine import Engine
from orchestrator.pipeline import Pipeline, Stage
from orchestrator.tests import fixture_stages
from orchestrator.tests.test_helpers import make_temp_git_repo


class EngineGateTest(unittest.TestCase):
    def setUp(self):
        fixture_stages.reset_fixture_state()
        self.repo = make_temp_git_repo()
        self.run_dir = self.repo / "_run"

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_dependent_stage_only_runs_after_dependency_passes(self):
        pipeline = Pipeline(name="p", description="", stages=[
            Stage(name="a", runner="orchestrator.tests.fixture_stages.always_pass"),
            Stage(name="b", runner="orchestrator.tests.fixture_stages.always_pass", depends_on=["a"]),
        ])
        engine = Engine(pipeline, "run1", self.run_dir, self.repo)
        terminal = engine.run()

        self.assertEqual(terminal, "completed")
        events = engine.audit.read_events()
        enter_order = [e["stage"] for e in events if e["event"] == "enter"]
        self.assertLess(enter_order.index("a"), enter_order.index("b"))

    def test_independent_stages_both_run(self):
        pipeline = Pipeline(name="p", description="", stages=[
            Stage(name="a", runner="orchestrator.tests.fixture_stages.always_pass"),
            Stage(name="b", runner="orchestrator.tests.fixture_stages.always_pass"),
        ])
        engine = Engine(pipeline, "run2", self.run_dir, self.repo)
        terminal = engine.run()

        self.assertEqual(terminal, "completed")
        self.assertEqual(engine.status["a"].value, "passed")
        self.assertEqual(engine.status["b"].value, "passed")

    def test_unreachable_stage_marked_skipped_after_upstream_failure(self):
        pipeline = Pipeline(name="p", description="", stages=[
            Stage(name="broken", runner="orchestrator.tests.fixture_stages.always_fail"),
            Stage(name="downstream", runner="orchestrator.tests.fixture_stages.always_pass",
                  depends_on=["broken"]),
        ])
        engine = Engine(pipeline, "run3", self.run_dir, self.repo)
        terminal = engine.run()

        self.assertEqual(terminal, "safe_stopped")
        self.assertEqual(engine.status["broken"].value, "failed")
        self.assertEqual(engine.status["downstream"].value, "skipped")


if __name__ == "__main__":
    unittest.main()
