#!/usr/bin/env bash
set -euo pipefail

python -m pip install -e .
python -m unittest discover -s tests -p 'test_*.py' -v

capstone-portfolio-ga \
  --recommendations data/layered_recommendations.csv \
  --history data/resultadoPruebasGatling.txt \
  --budget 20 --population 80 --generations 120 --runs 10 --seed 42 \
  --output-dir results

capstone-portfolio-aco \
  --portfolio results/selected_validation_portfolio.csv \
  --ants 40 --iterations 100 --runs 10 --seed 42 --random-samples 100 \
  --output-dir results/aco

python scripts/validate_outputs.py --ga-dir results --aco-dir results/aco --budget 20
