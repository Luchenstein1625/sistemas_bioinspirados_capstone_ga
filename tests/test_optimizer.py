import unittest

from validation_portfolio.data import Candidate
from validation_portfolio.genetic import GAConfig, PortfolioOptimizer


def candidate(index: int, pilar: str, component: str) -> Candidate:
    return Candidate(index, str(index), pilar, component, "GET", str(index % 3 + 1), str(index % 3 + 1), "medium", "medium", "low", "Success", "1", 0, 500 + index)


class OptimizerTests(unittest.TestCase):
    def setUp(self):
        items = [candidate(i, f"p{i%3}", f"c{i%5}") for i in range(15)]
        self.optimizer = PortfolioOptimizer(items, GAConfig(budget=5, population=12, generations=5), seed=7)

    def test_repair_preserves_budget(self):
        repaired = self.optimizer.repair(tuple(1 for _ in range(15)))
        self.assertEqual(sum(repaired), 5)

    def test_run_returns_valid_portfolio(self):
        best, history = self.optimizer.run()
        self.assertEqual(sum(best.chromosome), 5)
        self.assertEqual(len(history), 6)
        self.assertGreater(best.fitness, 0)


if __name__ == "__main__":
    unittest.main()
