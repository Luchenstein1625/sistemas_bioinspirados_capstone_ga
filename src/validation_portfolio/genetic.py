"""Algoritmo genético para seleccionar una cartera de validación Gatling.

Este módulo implementa un algoritmo genético clásico (Holland, 1975; Goldberg,
1989) sobre una representación binaria: cada gen indica si un candidato
`upgrade` entra (1) o no (0) a la cartera de validación experimental.

Diseño de seguridad: las restricciones duras (Estado=Success, Performance=1,
errorCount=0, p95 válido) se aplican ANTES de construir la lista de
candidatos (ver `data.load_candidates`), nunca como término del fitness. Esto
evita que un caso riesgoso compense su inseguridad aportando diversidad.

Nota de la versión 2 (corrección post-revisión):
La versión anterior sumaba dos términos del fitness -- `build_coverage`
(+0.05) y `redundancy_penalty` (-0.10) -- que resultaban ser matemáticamente
colineales: con presupuesto fijo, `redundancy = 1 - build_coverage`, por lo
que ambos términos codificaban la misma variable con distinto peso, no dos
objetivos independientes. Esta versión reemplaza la penalización de
redundancia por una medida de *concentración* (cuántos casos comparten el
build más repetido), que sí es información adicional: dos carteras pueden
tener la misma cantidad de builds distintos y, aun así, una puede concentrar
varios casos en un mismo build y la otra no.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .data import Candidate


@dataclass(frozen=True)
class GAConfig:
    """Hiperparámetros del algoritmo genético.

    Attributes:
        budget: número exacto de candidatos que debe contener cada cartera.
        population: tamaño de la población en cada generación.
        generations: número de generaciones a evolucionar.
        crossover_rate: probabilidad de aplicar cruzamiento uniforme.
        mutation_rate: probabilidad de invertir cada gen individual.
        elite: número de mejores individuos que pasan sin cambios a la
            siguiente generación (elitismo).
        tournament: tamaño del torneo de selección de padres.
    """

    budget: int = 20
    population: int = 80
    generations: int = 120
    crossover_rate: float = 0.85
    mutation_rate: float = 0.03
    elite: int = 4
    tournament: int = 4


@dataclass(frozen=True)
class Evaluation:
    """Resultado de evaluar un cromosoma: su fitness y el detalle por componente."""

    chromosome: tuple[int, ...]
    fitness: float
    details: dict[str, float | int]


class PortfolioOptimizer:
    """Optimiza qué subconjunto de `candidates` conforma la mejor cartera.

    Un individuo es un vector binario de longitud `len(candidates)`. La
    posición i vale 1 si el candidato i está incluido en la cartera.
    """

    def __init__(self, candidates: list[Candidate], config: GAConfig, seed: int = 42):
        if not 1 <= config.budget <= len(candidates):
            raise ValueError("Budget must be between 1 and the number of candidates.")
        self.candidates = candidates
        self.config = config
        # RNG dedicado a la evolución (selección, cruzamiento, mutación, reparación).
        self.rng = random.Random(seed)
        # RNG independiente para el baseline aleatorio de comparación, de modo
        # que no herede el estado consumido durante la corrida del GA.
        self.baseline_rng = random.Random(seed * 1_000_003 + 7)
        self.max_pilars = max(1, len({item.pilar for item in candidates}))
        self.max_components = max(1, len({item.component for item in candidates}))
        self.max_quadrants = max(1, len({item.proposed_quadrant for item in candidates}))
        self.max_configs = max(1, len({item.configuration for item in candidates}))
        self.cache: dict[tuple[int, ...], Evaluation] = {}

    def random_chromosome(self, rng: random.Random | None = None) -> tuple[int, ...]:
        """Genera una cartera aleatoria válida (exactamente `budget` genes en 1)."""
        rng = rng or self.rng
        selected = set(rng.sample(range(len(self.candidates)), self.config.budget))
        return tuple(1 if index in selected else 0 for index in range(len(self.candidates)))

    def repair(self, chromosome: tuple[int, ...]) -> tuple[int, ...]:
        """Ajusta un cromosoma para que tenga exactamente `budget` genes activos.

        El cruzamiento y la mutación pueden dejar más o menos genes en 1 que
        el presupuesto permitido; esta función agrega o quita genes al azar
        hasta recuperar la cardinalidad correcta.
        """
        genes = list(chromosome)
        selected = [index for index, bit in enumerate(genes) if bit]
        unselected = [index for index, bit in enumerate(genes) if not bit]
        while len(selected) > self.config.budget:
            index = self.rng.choice(selected)
            selected.remove(index)
            unselected.append(index)
            genes[index] = 0
        while len(selected) < self.config.budget:
            index = self.rng.choice(unselected)
            unselected.remove(index)
            selected.append(index)
            genes[index] = 1
        return tuple(genes)

    def evaluate(self, chromosome: tuple[int, ...]) -> Evaluation:
        """Calcula el fitness multiobjetivo de una cartera (con caché por cromosoma).

        Componentes (pesos entre paréntesis, todos sobre carteras del mismo
        tamaño `budget`, por lo que son comparables entre sí):
            pilar_coverage (0.30): fracción de pilares del universo cubiertos.
            component_coverage (0.20): fracción de componentes cubiertos,
                normalizada por min(componentes disponibles, presupuesto).
            quadrant_coverage (0.15): idem para cuadrantes propuestos.
            mean_historical_quality (0.20): calidad histórica promedio de los
                casos seleccionados (ver Candidate.historical_quality).
            configuration_coverage (0.10): diversidad de configuraciones
                (concurrencia, iteraciones, tiempo de respuesta esperado).
            build_coverage (0.05): fracción de builds distintos cubiertos.
            concentration_penalty (-0.10): penaliza que muchos casos
                seleccionados provengan del MISMO build, aunque el build
                coverage total ya sea alto. A diferencia de la versión previa
                (que penalizaba 1 - build_coverage, colineal con
                build_coverage), esta métrica usa el tamaño del grupo de
                build más repetido, que es información adicional real.
        """
        if chromosome in self.cache:
            return self.cache[chromosome]
        selected = [item for bit, item in zip(chromosome, self.candidates) if bit]
        budget = len(selected)

        pilars = len({item.pilar for item in selected}) / self.max_pilars
        components = len({item.component for item in selected}) / min(self.max_components, self.config.budget)
        quadrants = len({item.proposed_quadrant for item in selected}) / min(self.max_quadrants, self.config.budget)
        configurations = len({item.configuration for item in selected}) / min(self.max_configs, self.config.budget)
        builds = len({item.build_id for item in selected}) / self.config.budget
        quality = sum(item.historical_quality for item in selected) / budget

        build_counts: dict[str, int] = {}
        for item in selected:
            build_counts[item.build_id] = build_counts.get(item.build_id, 0) + 1
        max_repeats = max(build_counts.values(), default=1)
        # 0 si ningún build se repite, 1 si TODOS los casos vienen del mismo build.
        concentration = (max_repeats - 1) / max(1, budget - 1)

        fitness = (
            0.30 * pilars
            + 0.20 * components
            + 0.15 * quadrants
            + 0.20 * quality
            + 0.10 * configurations
            + 0.05 * builds
            - 0.10 * concentration
        )
        result = Evaluation(chromosome, round(fitness, 8), {
            "pilar_coverage": round(pilars, 6),
            "component_coverage": round(components, 6),
            "quadrant_coverage": round(quadrants, 6),
            "configuration_coverage": round(configurations, 6),
            "build_coverage": round(builds, 6),
            "mean_historical_quality": round(quality, 6),
            "concentration_penalty": round(concentration, 6),
        })
        self.cache[chromosome] = result
        return result

    def tournament(self, population: list[Evaluation]) -> tuple[int, ...]:
        """Selecciona un padre por torneo: el mejor de `tournament` individuos al azar."""
        return max(self.rng.sample(population, self.config.tournament), key=lambda item: item.fitness).chromosome

    def crossover(self, left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
        """Cruzamiento uniforme: cada gen del hijo viene al azar de un padre u otro."""
        if self.rng.random() >= self.config.crossover_rate:
            return left
        child = tuple(a if self.rng.random() < 0.5 else b for a, b in zip(left, right))
        return self.repair(child)

    def mutate(self, chromosome: tuple[int, ...]) -> tuple[int, ...]:
        """Mutación por inversión de bit con probabilidad `mutation_rate` por gen."""
        genes = list(chromosome)
        for index in range(len(genes)):
            if self.rng.random() < self.config.mutation_rate:
                genes[index] = 1 - genes[index]
        return self.repair(tuple(genes))

    def random_baseline(self, samples: int = 100) -> list[float]:
        """Genera `samples` carteras aleatorias válidas usando un RNG independiente
        del usado por la evolución, para que el baseline no dependa del estado
        interno dejado por una corrida previa del algoritmo genético."""
        return [self.evaluate(self.random_chromosome(self.baseline_rng)).fitness for _ in range(samples)]

    def run(self) -> tuple[Evaluation, list[dict[str, float | int]]]:
        """Ejecuta el ciclo evolutivo completo y retorna la mejor cartera y el historial."""
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
