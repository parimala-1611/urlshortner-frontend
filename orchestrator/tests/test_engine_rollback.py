import shutil
import subprocess
import unittest

from orchestrator.engine import Engine
from orchestrator.pipeline import Pipeline, Stage
from orchestrator.tests import fixture_stages
from orchestrator.tests.test_helpers import make_temp_git_repo


class EngineRollbackTest(unittest.TestCase):
    def setUp(self):
        fixture_stages.reset_fixture_state()
        self.repo = make_temp_git_repo()
        self.run_dir = self.repo / "_run"

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_rollback_restores_pre_stage_commit_on_unrecoverable_failure(self):
        pre_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo,
                                  capture_output=True, text=True, check=True).stdout.strip()

        pipeline = Pipeline(name="p", description="", stages=[
            Stage(name="broken", runner="orchestrator.tests.fixture_stages.commit_then_fail",
                  rollback_on_failure=True),
        ])
        engine = Engine(pipeline, "run-rollback", self.run_dir, self.repo)
        terminal = engine.run()

        self.assertEqual(terminal, "safe_stopped")

        post_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo,
                                   capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(post_sha, pre_sha)
        self.assertFalse((self.repo / "unwanted.txt").exists())

        events = engine.audit.read_events()
        self.assertTrue(any(e["event"] == "rollback" for e in events))


if __name__ == "__main__":
    unittest.main()
