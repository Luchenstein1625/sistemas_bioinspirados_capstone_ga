from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import asdict
from pathlib import Path
from statistics import mean, pstdev

from .aco import ACOConfig, ExecutionOrderACO, PortfolioCase


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Order a GA portfolio with Ant Colony Optimization")
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results/aco"))
    parser.add_argument("--ants", type=int, default=40)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--random-samples", type=int, default=100)
    return parser.parse_args()


def load_portfolio(path: Path) -> list[PortfolioCase]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    required = {
        "build_id", "pilar", "component", "proposed_quadrant",
        "proposed_concurrency", "proposed_iterations",
        "proposed_response_time", "historical_quality",
    }
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"Portfolio is missing columns: {sorted(missing)}")
    return [
        PortfolioCase(
            build_id=row["build_id"],
            pilar=row["pilar"],
            component=row["component"],
            proposed_quadrant=row["proposed_quadrant"],
            proposed_concurrency=row["proposed_concurrency"],
            proposed_iterations=row["proposed_iterations"],
            proposed_response_time=row["proposed_response_time"],
            historical_quality=float(row["historical_quality"]),
            row=row,
        )
        for row in rows
    ]


def write_svg(path: Path, history: list[dict[str, float | int]]) -> None:
    width, height, margin = 900, 500, 60
    xmax = max(int(row["iteration"]) for row in history) or 1
    values = [float(row[key]) for row in history for key in ("best_score", "mean_score")]
    ymin, ymax = min(values), max(values)
    span = max(0.001, ymax - ymin)
    def points(key: str) -> str:
        return " ".join(
            f"{margin+int(row['iteration'])/xmax*(width-2*margin):.1f},"
            f"{height-margin-(float(row[key])-ymin)/span*(height-2*margin):.1f}"
            for row in history
        )
    path.write_text(
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="500">
<rect width="100%" height="100%" fill="white"/>
<text x="450" y="30" text-anchor="middle" font-family="Arial" font-size="20">Convergencia ACO</text>
<line x1="60" y1="440" x2="840" y2="440" stroke="#333"/><line x1="60" y1="60" x2="60" y2="440" stroke="#333"/>
<polyline fill="none" stroke="#00897b" stroke-width="3" points="{points('best_score')}"/>
<polyline fill="none" stroke="#f57c00" stroke-width="2" points="{points('mean_score')}"/>
<text x="450" y="485" text-anchor="middle" font-family="Arial">Iteración</text>
<text x="18" y="250" transform="rotate(-90 18 250)" text-anchor="middle" font-family="Arial">Score de secuencia</text>
</svg>''', encoding="utf-8")


def main() -> None:
    options = arguments()
    options.output_dir.mkdir(parents=True, exist_ok=True)
    cases = load_portfolio(options.portfolio)
    config = ACOConfig(ants=options.ants, iterations=options.iterations)
    runs = []
    executions = []
    for run in range(options.runs):
        optimizer = ExecutionOrderACO(cases, config, options.seed + run)
        result, history = optimizer.run()
        executions.append((result, history, optimizer))
        runs.append({"run": run + 1, "seed": options.seed + run, "score": result.score})
    best, history, optimizer = max(executions, key=lambda item: item[0].score)

    random_rng = random.Random(options.seed * 1_000_003 + 11)
    random_scores = []
    for _ in range(options.random_samples):
        route = list(range(len(cases)))
        random_rng.shuffle(route)
        random_scores.append(optimizer.evaluate(tuple(route)).score)
    greedy_quality = optimizer.evaluate(tuple(sorted(
        range(len(cases)), key=lambda index: cases[index].historical_quality, reverse=True
    )))
    greedy_transition = optimizer.greedy_route()

    plan_path = options.output_dir / "aco_execution_plan.csv"
    fields = ["execution_order", "source_priority", *cases[0].row.keys()]
    with plan_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for order, index in enumerate(best.route, 1):
            row = dict(cases[index].row)
            writer.writerow({"execution_order": order, "source_priority": row.get("priority", ""), **row})

    with (options.output_dir / "aco_independent_runs.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["run", "seed", "score"])
        writer.writeheader(); writer.writerows(runs)
    with (options.output_dir / "aco_history.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=history[0].keys())
        writer.writeheader(); writer.writerows(history)
    comparison = [
        {"method": "random_mean", "score": round(mean(random_scores), 8)},
        {"method": "quality_order", "score": greedy_quality.score},
        {"method": "greedy_transition", "score": greedy_transition.score},
        {"method": "aco", "score": best.score},
    ]
    with (options.output_dir / "aco_comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["method", "score"])
        writer.writeheader(); writer.writerows(comparison)
    methodology = {
        "purpose": "Order the 20 cases selected by GA; ACO does not re-select the portfolio.",
        "config": asdict(config),
        "runs": options.runs,
        "seed": options.seed,
        "objective_weights": {
            "transition_efficiency": 0.50,
            "early_coverage_auc": 0.35,
            "early_quality": 0.15,
        },
        "transition_proxy_weights": {
            "parameter_distance": 0.35,
            "quadrant_change": 0.25,
            "pilar_change": 0.25,
            "component_change": 0.15,
        },
        "warning": "Transition costs are academic proxies, not observed duration or monetary cost. Gatling execution and human approval remain pending.",
    }
    (options.output_dir / "aco_methodology.json").write_text(
        json.dumps(methodology, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_svg(options.output_dir / "aco_convergence.svg", history)
    summary = {
        "cases": len(cases),
        "aco_best": best.score,
        "aco_mean": round(mean(item["score"] for item in runs), 8),
        "aco_std": round(pstdev(item["score"] for item in runs), 8),
        "random_mean": round(mean(random_scores), 8),
        "quality_order": greedy_quality.score,
        "greedy_transition": greedy_transition.score,
        "best_components": {
            "transition_efficiency": best.transition_efficiency,
            "early_coverage_auc": best.early_coverage_auc,
            "early_quality": best.early_quality,
        },
        "status": "pending_new_execution",
    }
    (options.output_dir / "aco_best_solution.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

