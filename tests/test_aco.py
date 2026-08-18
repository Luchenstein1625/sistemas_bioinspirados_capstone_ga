import unittest

from validation_portfolio.aco import ACOConfig, ExecutionOrderACO, PortfolioCase


def cases() -> list[PortfolioCase]:
    rows = []
    for index in range(8):
        row = {
            "priority": str(index + 1),
            "build_id": str(1000 + index),
            "pilar": f"p{index % 2}",
            "component": f"c{index % 4}",
            "proposed_quadrant": str(index % 3),
            "proposed_concurrency": ["low", "medium", "high"][index % 3],
            "proposed_iterations": ["low", "medium"][index % 2],
            "proposed_response_time": ["medium", "high"][index % 2],
            "historical_quality": str(0.90 + index / 100),
        }
        rows.append(PortfolioCase(
            build_id=row["build_id"], pilar=row["pilar"], component=row["component"],
            proposed_quadrant=row["proposed_quadrant"],
            proposed_concurrency=row["proposed_concurrency"],
            proposed_iterations=row["proposed_iterations"],
            proposed_response_time=row["proposed_response_time"],
            historical_quality=float(row["historical_quality"]), row=row,
        ))
    return rows


class ACOTests(unittest.TestCase):
    def test_aco_returns_complete_permutation(self):
        optimizer = ExecutionOrderACO(cases(), ACOConfig(ants=10, iterations=8), seed=7)
        best, history = optimizer.run()
        self.assertEqual(sorted(best.route), list(range(8)))
        self.assertEqual(len(history), 8)
        self.assertTrue(0.0 <= best.score <= 1.0)

    def test_aco_is_reproducible_for_same_seed(self):
        config = ACOConfig(ants=8, iterations=6)
        left, _ = ExecutionOrderACO(cases(), config, seed=19).run()
        right, _ = ExecutionOrderACO(cases(), config, seed=19).run()
        self.assertEqual(left, right)

    def test_invalid_route_is_rejected(self):
        optimizer = ExecutionOrderACO(cases(), ACOConfig(ants=4, iterations=2), seed=1)
        with self.assertRaises(ValueError):
            optimizer.evaluate((0, 1, 2))


if __name__ == "__main__":
    unittest.main()
