import unittest

from orchestrator.pipeline import Pipeline, Stage


class PipelineValidationTest(unittest.TestCase):
    def test_rejects_unknown_dependency(self):
        stages = [Stage(name="a", runner="x.y", depends_on=["ghost"])]
        with self.assertRaises(ValueError):
            Pipeline._validate_graph(stages)

    def test_rejects_cycle(self):
        stages = [
            Stage(name="a", runner="x.y", depends_on=["b"]),
            Stage(name="b", runner="x.y", depends_on=["a"]),
        ]
        with self.assertRaises(ValueError):
            Pipeline._validate_graph(stages)

    def test_accepts_valid_dag(self):
        stages = [
            Stage(name="a", runner="x.y"),
            Stage(name="b", runner="x.y", depends_on=["a"]),
        ]
        Pipeline._validate_graph(stages)  # should not raise


if __name__ == "__main__":
    unittest.main()
