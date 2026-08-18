from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate GA + ACO offline artifacts")
    parser.add_argument("--ga-dir", type=Path, default=Path("results"))
    parser.add_argument("--aco-dir", type=Path, default=Path("results/aco"))
    parser.add_argument("--budget", type=int, default=20)
    options = parser.parse_args()

    ga_solution = json.loads((options.ga_dir / "best_solution.json").read_text(encoding="utf-8"))
    ga_rows = list(csv.DictReader((options.ga_dir / "selected_validation_portfolio.csv").open(encoding="utf-8")))
    aco_rows = list(csv.DictReader((options.aco_dir / "aco_execution_plan.csv").open(encoding="utf-8")))
    aco_solution = json.loads((options.aco_dir / "aco_best_solution.json").read_text(encoding="utf-8"))

    assert ga_solution["safety_constraints_satisfied"] is True
    assert ga_solution["online_validation_status"] == "pending_new_execution"
    assert len(ga_rows) == options.budget
    assert len(aco_rows) == options.budget
    assert [int(row["execution_order"]) for row in aco_rows] == list(range(1, options.budget + 1))
    assert {row["build_id"] for row in ga_rows} == {row["build_id"] for row in aco_rows}
    assert all(row["status"].lower() == "success" for row in ga_rows)
    assert all(float(row["error_count"]) == 0 for row in ga_rows)
    assert all(row["performance"] == "1" for row in ga_rows)
    assert all(0 < float(row["p95_ms"]) <= 1500 for row in ga_rows)
    assert aco_solution["cases"] == options.budget
    assert aco_solution["status"] == "pending_new_execution"
    print("OK: GA and ACO artifacts are structurally valid; online Gatling validation remains pending.")


if __name__ == "__main__":
    main()

