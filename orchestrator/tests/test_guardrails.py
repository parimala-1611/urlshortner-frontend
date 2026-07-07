import shutil
import subprocess
import unittest

from orchestrator import guardrails
from orchestrator.tests.test_helpers import make_temp_git_repo


class GuardrailsTest(unittest.TestCase):
    def setUp(self):
        self.repo = make_temp_git_repo()
        self.base_ref = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo,
                                        capture_output=True, text=True, check=True).stdout.strip()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def _commit(self, filename: str, content: str) -> None:
        (self.repo / filename).write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", f"add {filename}"], cwd=self.repo, check=True)

    def test_detects_secret_pattern(self):
        self._commit("config.txt", 'api_key = "abcdefghijklmnopqrstuvwx"\n')
        ok, _ = guardrails.no_secrets_in_diff(self.repo, self.base_ref)
        self.assertFalse(ok)

    def test_clean_diff_passes(self):
        self._commit("readme2.txt", "just some text\n")
        ok, _ = guardrails.no_secrets_in_diff(self.repo, self.base_ref)
        self.assertTrue(ok)

    def test_detects_protected_file_touch(self):
        (self.repo / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        self._commit(".github/workflows/ci.yml", "name: ci\n")
        ok, _ = guardrails.no_protected_files_touched(self.repo, self.base_ref)
        self.assertFalse(ok)

    def test_change_size_bound(self):
        for i in range(5):
            self._commit(f"file{i}.txt", "x\n")
        ok, _ = guardrails.change_size_within_bounds(self.repo, self.base_ref, max_files=3)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
