import shutil
import unittest

from orchestrator.engine import Engine
from orchestrator.metrics import compute_run_metrics
from orchestrator.pipeline import Pipeline, Stage
from orchestrator.tests import fixture_stages
from orchestrator.tests.test_helpers import make_temp_git_repo


class MetricsTest(unittest.TestCase):
    def setUp(self):
        fixture_stages.reset_fixture_state()
        self.repo = make_temp_git_repo()
        self.run_dir = self.repo / "_run"

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_metrics_reflect_retries_and_success_rate(self):
        pipeline = Pipeline(name="p", description="", stages=[
            Stage(name="flaky", runner="orchestrator.tests.fixture_stages.flaky_then_pass",
                  max_retries=2, retry_backoff_seconds=0,
                  params={"key": "metrics-test-1", "fail_times": 1}),
            Stage(name="ok", runner="orchestrator.tests.fixture_stages.always_pass"),
        ])
        engine = Engine(pipeline, "run-metrics", self.run_dir, self.repo)
        engine.run()

        report = compute_run_metrics(self.run_dir)
        self.assertEqual(report["stages_passed"], 2)
        self.assertEqual(report["retry_count"], 1)
        self.assertGreaterEqual(report["success_rate"], 0)
        self.assertIsNotNone(report["end_to_end_latency_seconds"])

    def test_missing_run_reports_error(self):
        report = compute_run_metrics(self.repo / "no_such_run")
        self.assertIn("error", report)


if __name__ == "__main__":
    unittest.main()
