import shutil
import unittest

from orchestrator.engine import Engine
from orchestrator.metrics import compute_run_metrics
from orchestrator.pipeline import Pipeline, Stage
from orchestrator.tests import fixture_stages
from orchestrator.tests.test_helpers import make_temp_git_repo


class EngineApprovalTest(unittest.TestCase):
    def setUp(self):
        fixture_stages.reset_fixture_state()
        self.repo = make_temp_git_repo()
        self.run_dir = self.repo / "_run"

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def _pipeline(self):
        return Pipeline(name="p", description="", stages=[
            Stage(name="gate", runner="orchestrator.tests.fixture_stages.always_pass",
                  requires_approval=True),
            Stage(name="after", runner="orchestrator.tests.fixture_stages.always_pass",
                  depends_on=["gate"]),
        ])

    def test_approval_required_stage_halts_run(self):
        engine = Engine(self._pipeline(), "run-approval", self.run_dir, self.repo)
        terminal = engine.run()

        self.assertEqual(terminal, "awaiting_approval")
        self.assertEqual(engine.status["gate"].value, "pending")
        self.assertEqual(engine.status["after"].value, "pending")
        self.assertTrue((self.run_dir / "pending_approval.json").exists())
        events = engine.audit.read_events()
        self.assertTrue(any(e["event"] == "approval_requested" for e in events))

    def test_resumed_engine_with_approval_completes(self):
        engine = Engine(self._pipeline(), "run-approval-2", self.run_dir, self.repo)
        engine.run()

        resumed = Engine.resume(self._pipeline(), "run-approval-2", self.run_dir, self.repo)
        resumed.approvals.add("gate")
        terminal = resumed.run()

        self.assertEqual(terminal, "completed")
        self.assertEqual(resumed.status["gate"].value, "passed")
        self.assertEqual(resumed.status["after"].value, "passed")

    def test_approval_pause_then_resume_does_not_skew_success_rate(self):
        engine = Engine(self._pipeline(), "run-approval-3", self.run_dir, self.repo)
        engine.run()

        resumed = Engine.resume(self._pipeline(), "run-approval-3", self.run_dir, self.repo)
        resumed.approvals.add("gate")
        resumed.run()

        report = compute_run_metrics(self.run_dir)
        # Both stages actually passed; the approval pause/resume must not look
        # like a failed attempt in the reliability metrics.
        self.assertEqual(report["stages_attempted"], 2)
        self.assertEqual(report["stages_passed"], 2)
        self.assertEqual(report["success_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
