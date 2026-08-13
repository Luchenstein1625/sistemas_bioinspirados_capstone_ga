from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean, pstdev

from .data import Candidate, load_candidates
from .genetic import GAConfig, PortfolioOptimizer


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select a Gatling validation portfolio with a GA")
    parser.add_argument("--recommendations", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=20)
    parser.add_argument("--population", type=int, default=80)
    parser.add_argument("--generations", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    return parser.parse_args()


def selected_rows(evaluation, candidates: list[Candidate]) -> list[Candidate]:
    return [candidate for bit, candidate in zip(evaluation.chromosome, candidates) if bit]


def greedy_solution(optimizer: PortfolioOptimizer):
    ranked = sorted(range(len(optimizer.candidates)), key=lambda i: optimizer.candidates[i].historical_quality, reverse=True)
    chromosome = tuple(1 if index in set(ranked[: optimizer.config.budget]) else 0 for index in range(len(ranked)))
    return optimizer.evaluate(chromosome)


def write_svg(path: Path, history: list[dict]) -> None:
    width, height, margin = 900, 500, 60
    xmax = max(row["generation"] for row in history) or 1
    values = [row[key] for row in history for key in ("best_fitness", "mean_fitness")]
    ymin, ymax = min(values), max(values); span = max(0.001, ymax - ymin)
    def points(key):
        return " ".join(f"{margin+row['generation']/xmax*(width-2*margin):.1f},{height-margin-(row[key]-ymin)/span*(height-2*margin):.1f}" for row in history)
    ticks = []
    for step in range(5):
        value = ymin + span * step / 4
        y = height - margin - step / 4 * (height - 2 * margin)
        ticks.append(
            f'<line x1="55" y1="{y:.1f}" x2="840" y2="{y:.1f}" stroke="#e5e7eb"/>'
            f'<text x="50" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{value:.3f}</text>'
        )
    path.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="500"><rect width="100%" height="100%" fill="white"/><text x="450" y="28" text-anchor="middle" font-family="Arial" font-size="20">Evolución del fitness de cartera</text>{''.join(ticks)}<line x1="60" y1="440" x2="840" y2="440" stroke="#333"/><line x1="60" y1="60" x2="60" y2="440" stroke="#333"/><polyline fill="none" stroke="#1565c0" stroke-width="3" points="{points('best_fitness')}"/><polyline fill="none" stroke="#f57c00" stroke-width="2" points="{points('mean_fitness')}"/><text x="450" y="485" text-anchor="middle" font-family="Arial">Generación</text><text x="16" y="250" transform="rotate(-90 16 250)" text-anchor="middle" font-family="Arial">Fitness</text><line x1="610" y1="45" x2="640" y2="45" stroke="#1565c0" stroke-width="3"/><text x="647" y="49" font-family="Arial" font-size="12">Mejor fitness</text><line x1="735" y1="45" x2="765" y2="45" stroke="#f57c00" stroke-width="2"/><text x="772" y="49" font-family="Arial" font-size="12">Promedio</text></svg>''', encoding="utf-8")


def main() -> None:
    options = args(); options.output_dir.mkdir(parents=True, exist_ok=True)
    candidates = load_candidates(options.recommendations, options.history)
    config = GAConfig(budget=options.budget, population=options.population, generations=options.generations)
    independent = []
    run_results = []
    for run in range(options.runs):
        optimizer = PortfolioOptimizer(candidates, config, options.seed + run)
        result, run_history = optimizer.run()
        run_results.append((result, run_history, optimizer))
        independent.append({"run": run + 1, "seed": options.seed + run, "fitness": result.fitness})
    best, history, optimizer = max(run_results, key=lambda item: item[0].fitness)
    greedy = greedy_solution(optimizer)
    random_scores = [optimizer.evaluate(optimizer.random_chromosome()).fitness for _ in range(100)]
    random_mean = sum(random_scores) / len(random_scores)

    rows = selected_rows(best, candidates)
    with (options.output_dir / "selected_validation_portfolio.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = ["priority", "build_id", "pilar", "component", "method", "current_quadrant", "proposed_quadrant", "proposed_concurrency", "proposed_iterations", "proposed_response_time", "historical_quality", "status", "performance", "error_count", "p95_ms", "approval_status"]
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for priority, item in enumerate(sorted(rows, key=lambda x: x.historical_quality, reverse=True), 1):
            writer.writerow({"priority": priority, **{name: getattr(item, name) for name in fields if hasattr(item, name)}, "historical_quality": round(item.historical_quality, 6), "approval_status": "human_review_required"})

    solution = {"candidate_count": len(candidates), "budget": options.budget, "fitness": best.fitness, "fitness_components": best.details, "selected_indexes": [i for i, bit in enumerate(best.chromosome) if bit], "safety_constraints_satisfied": True, "online_validation_status": "pending_new_execution", "human_approval_required": True}
    (options.output_dir / "best_solution.json").write_text(json.dumps(solution, indent=2, ensure_ascii=False), encoding="utf-8")
    methodology = {"seed": options.seed, "config": config.__dict__, "hard_safety_constraints": {"Estado": "Success", "Performance": "1", "errorCount": 0, "p95_ms": "0 < p95 <= 1500"}, "weights": {"pilar_diversity": 0.30, "component_diversity": 0.20, "quadrant_diversity": 0.15, "historical_quality": 0.20, "configuration_diversity": 0.10, "build_coverage": 0.05, "redundancy_penalty": 0.10}, "warning": "Weights are academic assumptions; selected upgrades require specialist approval and new Gatling executions."}
    (options.output_dir / "methodology.json").write_text(json.dumps(methodology, indent=2, ensure_ascii=False), encoding="utf-8")
    with (options.output_dir / "fitness_history.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=history[0].keys()); writer.writeheader(); writer.writerows(history)
    with (options.output_dir / "comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["method", "fitness"]); writer.writeheader(); writer.writerows([{"method": "random_mean_100", "fitness": round(random_mean, 8)}, {"method": "greedy_quality", "fitness": greedy.fitness}, {"method": "genetic_algorithm", "fitness": best.fitness}])
    with (options.output_dir / "independent_runs.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["run", "seed", "fitness"]); writer.writeheader(); writer.writerows(independent)
    write_svg(options.output_dir / "fitness_evolution.svg", history)
    print(json.dumps({"candidates": len(candidates), "selected": len(rows), "random_mean": round(random_mean, 8), "greedy": greedy.fitness, "genetic_best": best.fitness, "genetic_mean": round(mean(item["fitness"] for item in independent), 8), "genetic_std": round(pstdev(item["fitness"] for item in independent), 8), "coverage": best.details}, indent=2))


if __name__ == "__main__":
    main()
