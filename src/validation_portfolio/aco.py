"""ACO para ordenar la cartera ya seleccionada por el algoritmo genético.

El AG responde *qué casos validar*. Este módulo responde *en qué orden
validarlos*. Los costos usados son proxies reproducibles construidos desde los
campos disponibles; no representan costos monetarios ni duraciones observadas.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


LEVELS = {
    "very_low": 0.0,
    "low": 0.25,
    "medium": 0.5,
    "high": 0.75,
    "very_high": 1.0,
}


@dataclass(frozen=True)
class PortfolioCase:
    build_id: str
    pilar: str
    component: str
    proposed_quadrant: str
    proposed_concurrency: str
    proposed_iterations: str
    proposed_response_time: str
    historical_quality: float
    row: dict[str, str]

    @property
    def configuration(self) -> tuple[str, str, str]:
        return (
            self.proposed_concurrency,
            self.proposed_iterations,
            self.proposed_response_time,
        )


@dataclass(frozen=True)
class ACOConfig:
    ants: int = 40
    iterations: int = 100
    alpha: float = 1.0
    beta: float = 2.0
    evaporation: float = 0.25
    q: float = 1.0
    elite_ants: int = 5


@dataclass(frozen=True)
class RouteEvaluation:
    route: tuple[int, ...]
    score: float
    transition_efficiency: float
    early_coverage_auc: float
    early_quality: float


class ExecutionOrderACO:
    """Optimiza una permutación de la cartera seleccionada por el AG."""

    def __init__(self, cases: list[PortfolioCase], config: ACOConfig, seed: int = 42):
        if len(cases) < 2:
            raise ValueError("ACO requires at least two portfolio cases.")
        if config.ants < 2 or config.iterations < 1:
            raise ValueError("ACO requires at least two ants and one iteration.")
        if not 0.0 < config.evaporation < 1.0:
            raise ValueError("Evaporation must be between 0 and 1.")
        self.cases = cases
        self.config = config
        self.rng = random.Random(seed)
        self.n = len(cases)
        self.pheromone = [[1.0 for _ in cases] for _ in cases]
        self.start_pheromone = [1.0 for _ in cases]
        self._universe = {
            "pilar": max(1, len({case.pilar for case in cases})),
            "component": max(1, len({case.component for case in cases})),
            "quadrant": max(1, len({case.proposed_quadrant for case in cases})),
            "configuration": max(1, len({case.configuration for case in cases})),
        }

    @staticmethod
    def _level(value: str) -> float:
        return LEVELS.get(value.strip().lower(), 0.5)

    def transition_cost(self, left: int, right: int) -> float:
        """Proxy [0,1] del esfuerzo de cambiar entre dos configuraciones."""
        a, b = self.cases[left], self.cases[right]
        parameter_distance = (
            abs(self._level(a.proposed_concurrency) - self._level(b.proposed_concurrency))
            + abs(self._level(a.proposed_iterations) - self._level(b.proposed_iterations))
            + abs(self._level(a.proposed_response_time) - self._level(b.proposed_response_time))
        ) / 3.0
        quadrant_change = float(a.proposed_quadrant != b.proposed_quadrant)
        pilar_change = float(a.pilar != b.pilar)
        component_change = float(a.component != b.component)
        return (
            0.35 * parameter_distance
            + 0.25 * quadrant_change
            + 0.25 * pilar_change
            + 0.15 * component_change
        )

    def _novelty(self, candidate: int, visited: set[int]) -> float:
        if not visited:
            return 1.0
        item = self.cases[candidate]
        selected = [self.cases[index] for index in visited]
        return (
            0.30 * float(item.pilar not in {case.pilar for case in selected})
            + 0.30 * float(item.component not in {case.component for case in selected})
            + 0.20 * float(item.proposed_quadrant not in {case.proposed_quadrant for case in selected})
            + 0.20 * float(item.configuration not in {case.configuration for case in selected})
        )

    def heuristic(self, previous: int | None, candidate: int, visited: set[int]) -> float:
        efficiency = 1.0 if previous is None else 1.0 - self.transition_cost(previous, candidate)
        quality = self.cases[candidate].historical_quality
        novelty = self._novelty(candidate, visited)
        return max(1e-9, 0.55 * efficiency + 0.25 * quality + 0.20 * novelty)

    def evaluate(self, route: tuple[int, ...]) -> RouteEvaluation:
        if len(route) != self.n or set(route) != set(range(self.n)):
            raise ValueError("Route must be a permutation of all portfolio cases.")
        costs = [self.transition_cost(a, b) for a, b in zip(route, route[1:])]
        efficiency = 1.0 - (sum(costs) / len(costs))

        seen_pilars: set[str] = set()
        seen_components: set[str] = set()
        seen_quadrants: set[str] = set()
        seen_configs: set[tuple[str, str, str]] = set()
        coverage_curve = []
        for index in route:
            case = self.cases[index]
            seen_pilars.add(case.pilar)
            seen_components.add(case.component)
            seen_quadrants.add(case.proposed_quadrant)
            seen_configs.add(case.configuration)
            coverage_curve.append(
                0.30 * len(seen_pilars) / self._universe["pilar"]
                + 0.30 * len(seen_components) / self._universe["component"]
                + 0.20 * len(seen_quadrants) / self._universe["quadrant"]
                + 0.20 * len(seen_configs) / self._universe["configuration"]
            )
        coverage_auc = sum(coverage_curve) / self.n

        weights = [1.0 / math.log2(position + 2.0) for position in range(self.n)]
        early_quality = sum(
            weight * self.cases[index].historical_quality
            for weight, index in zip(weights, route)
        ) / sum(weights)
        score = 0.50 * efficiency + 0.35 * coverage_auc + 0.15 * early_quality
        return RouteEvaluation(
            route=route,
            score=round(score, 8),
            transition_efficiency=round(efficiency, 8),
            early_coverage_auc=round(coverage_auc, 8),
            early_quality=round(early_quality, 8),
        )

    def _weighted_choice(self, options: list[int], weights: list[float]) -> int:
        total = sum(weights)
        threshold = self.rng.random() * total
        cumulative = 0.0
        for option, weight in zip(options, weights):
            cumulative += weight
            if cumulative >= threshold:
                return option
        return options[-1]

    def construct_route(self) -> tuple[int, ...]:
        remaining = list(range(self.n))
        start_weights = [
            self.start_pheromone[index] ** self.config.alpha
            * self.heuristic(None, index, set()) ** self.config.beta
            for index in remaining
        ]
        first = self._weighted_choice(remaining, start_weights)
        route = [first]
        remaining.remove(first)
        while remaining:
            visited = set(route)
            previous = route[-1]
            weights = [
                self.pheromone[previous][candidate] ** self.config.alpha
                * self.heuristic(previous, candidate, visited) ** self.config.beta
                for candidate in remaining
            ]
            chosen = self._weighted_choice(remaining, weights)
            route.append(chosen)
            remaining.remove(chosen)
        return tuple(route)

    def greedy_route(self) -> RouteEvaluation:
        route: list[int] = []
        remaining = set(range(self.n))
        while remaining:
            previous = route[-1] if route else None
            chosen = max(
                remaining,
                key=lambda index: self.heuristic(previous, index, set(route)),
            )
            route.append(chosen)
            remaining.remove(chosen)
        return self.evaluate(tuple(route))

    def run(self) -> tuple[RouteEvaluation, list[dict[str, float | int]]]:
        best: RouteEvaluation | None = None
        history = []
        for iteration in range(self.config.iterations):
            colony = [self.evaluate(self.construct_route()) for _ in range(self.config.ants)]
            colony.sort(key=lambda result: result.score, reverse=True)
            if best is None or colony[0].score > best.score:
                best = colony[0]
            retain = 1.0 - self.config.evaporation
            self.start_pheromone = [max(1e-9, value * retain) for value in self.start_pheromone]
            self.pheromone = [
                [max(1e-9, value * retain) for value in row]
                for row in self.pheromone
            ]
            for rank, result in enumerate(colony[: self.config.elite_ants], 1):
                deposit = self.config.q * result.score / rank
                self.start_pheromone[result.route[0]] += deposit
                for left, right in zip(result.route, result.route[1:]):
                    self.pheromone[left][right] += deposit
            history.append({
                "iteration": iteration,
                "best_score": best.score,
                "mean_score": round(sum(item.score for item in colony) / len(colony), 8),
            })
        assert best is not None
        return best, history

