from __future__ import annotations

import random
from dataclasses import dataclass

from .data import Candidate


@dataclass(frozen=True)
class GAConfig:
    budget: int = 20
    population: int = 80
    generations: int = 120
    crossover_rate: float = 0.85
    mutation_rate: float = 0.03
    elite: int = 4
    tournament: int = 4


@dataclass(frozen=True)
class Evaluation:
    chromosome: tuple[int, ...]
    fitness: float
    details: dict[str, float | int]


class PortfolioOptimizer:
    def __init__(self, candidates: list[Candidate], config: GAConfig, seed: int = 42):
        if not 1 <= config.budget <= len(candidates):
            raise ValueError("Budget must be between 1 and the number of candidates.")
        self.candidates = candidates
        self.config = config
        self.rng = random.Random(seed)
        self.max_pilars = max(1, len({item.pilar for item in candidates}))
        self.max_components = max(1, len({item.component for item in candidates}))
        self.max_quadrants = max(1, len({item.proposed_quadrant for item in candidates}))
        self.max_configs = max(1, len({item.configuration for item in candidates}))
        self.cache: dict[tuple[int, ...], Evaluation] = {}

    def random_chromosome(self) -> tuple[int, ...]:
        selected = set(self.rng.sample(range(len(self.candidates)), self.config.budget))
        return tuple(1 if index in selected else 0 for index in range(len(self.candidates)))

    def repair(self, chromosome: tuple[int, ...]) -> tuple[int, ...]:
        genes = list(chromosome)
        selected = [index for index, bit in enumerate(genes) if bit]
        unselected = [index for index, bit in enumerate(genes) if not bit]
        while len(selected) > self.config.budget:
            index = self.rng.choice(selected); selected.remove(index); unselected.append(index); genes[index] = 0
        while len(selected) < self.config.budget:
            index = self.rng.choice(unselected); unselected.remove(index); selected.append(index); genes[index] = 1
        return tuple(genes)

    def evaluate(self, chromosome: tuple[int, ...]) -> Evaluation:
        if chromosome in self.cache:
            return self.cache[chromosome]
        selected = [item for bit, item in zip(chromosome, self.candidates) if bit]
        pilars = len({item.pilar for item in selected}) / self.max_pilars
        components = len({item.component for item in selected}) / min(self.max_components, self.config.budget)
        quadrants = len({item.proposed_quadrant for item in selected}) / min(self.max_quadrants, self.config.budget)
        configurations = len({item.configuration for item in selected}) / min(self.max_configs, self.config.budget)
        builds = len({item.build_id for item in selected}) / self.config.budget
        quality = sum(item.historical_quality for item in selected) / len(selected)
        redundancy = 1.0 - builds
        fitness = (
            0.30 * pilars
            + 0.20 * components
            + 0.15 * quadrants
            + 0.20 * quality
            + 0.10 * configurations
            + 0.05 * builds
            - 0.10 * redundancy
        )
        result = Evaluation(chromosome, round(fitness, 8), {
            "pilar_coverage": round(pilars, 6),
            "component_coverage": round(components, 6),
            "quadrant_coverage": round(quadrants, 6),
            "configuration_coverage": round(configurations, 6),
            "build_coverage": round(builds, 6),
            "mean_historical_quality": round(quality, 6),
            "redundancy": round(redundancy, 6),
        })
        self.cache[chromosome] = result
        return result

    def tournament(self, population: list[Evaluation]) -> tuple[int, ...]:
        return max(self.rng.sample(population, self.config.tournament), key=lambda item: item.fitness).chromosome

    def crossover(self, left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
        if self.rng.random() >= self.config.crossover_rate:
            return left
        child = tuple(a if self.rng.random() < 0.5 else b for a, b in zip(left, right))
        return self.repair(child)

    def mutate(self, chromosome: tuple[int, ...]) -> tuple[int, ...]:
        genes = list(chromosome)
        for index in range(len(genes)):
            if self.rng.random() < self.config.mutation_rate:
                genes[index] = 1 - genes[index]
        return self.repair(tuple(genes))

    def run(self) -> tuple[Evaluation, list[dict[str, float | int]]]:
        population = [self.evaluate(self.random_chromosome()) for _ in range(self.config.population)]
        history = []
        best = max(population, key=lambda item: item.fitness)
        for generation in range(self.config.generations + 1):
            population.sort(key=lambda item: item.fitness, reverse=True)
            if population[0].fitness > best.fitness:
                best = population[0]
            history.append({
                "generation": generation,
                "best_fitness": best.fitness,
                "mean_fitness": round(sum(item.fitness for item in population) / len(population), 8),
            })
            if generation == self.config.generations:
                break
            children = [item.chromosome for item in population[: self.config.elite]]
            while len(children) < self.config.population:
                child = self.crossover(self.tournament(population), self.tournament(population))
                children.append(self.mutate(child))
            population = [self.evaluate(child) for child in children]
        return best, history

