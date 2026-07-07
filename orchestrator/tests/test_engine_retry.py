import shutil
import unittest

from orchestrator.engine import Engine
from orchestrator.pipeline import Pipeline, Stage
from orchestrator.tests import fixture_stages
from orchestrator.tests.test_helpers import make_temp_git_repo


class EngineRetryTest(unittest.TestCase):
    def setUp(self):
        fixture_stages.reset_fixture_state()
        self.repo = make_temp_git_repo()
        self.run_dir = self.repo / "_run"

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_bounded_retry_recovers_flaky_stage(self):
        pipeline = Pipeline(name="p", description="", stages=[
            Stage(name="flaky", runner="orchestrator.tests.fixture_stages.flaky_then_pass",
                  max_retries=3, retry_backoff_seconds=0,
                  params={"key": "retry-test-1", "fail_times": 2}),
        ])
        engine = Engine(pipeline, "run-retry", self.run_dir, self.repo)
        terminal = engine.run()

        self.assertEqual(terminal, "completed")
        self.assertEqual(engine.status["flaky"].value, "passed")
        self.assertEqual(engine.retries_used["flaky"], 2)
        events = engine.audit.read_events()
        self.assertEqual(len([e for e in events if e["event"] == "retry"]), 2)

    def test_exhausting_retries_safe_stops(self):
        pipeline = Pipeline(name="p", description="", stages=[
            Stage(name="flaky", runner="orchestrator.tests.fixture_stages.flaky_then_pass",
                  max_retries=1, retry_backoff_seconds=0,
                  params={"key": "retry-test-2", "fail_times": 5}),
        ])
        engine = Engine(pipeline, "run-retry-2", self.run_dir, self.repo)
        terminal = engine.run()

        self.assertEqual(terminal, "safe_stopped")
        self.assertEqual(engine.status["flaky"].value, "failed")


if __name__ == "__main__":
    unittest.main()
