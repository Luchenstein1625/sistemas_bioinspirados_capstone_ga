# Validación del flujo AG + ACO

## Alcance

El algoritmo genético selecciona 20 casos entre los candidatos factibles. ACO
recibe exactamente esos 20 casos y propone un orden experimental. ACO no cambia
la decisión `upgrade` ni reemplaza la revisión humana o la ejecución Gatling.

## Ejecución completa en Windows PowerShell

```powershell
git clone https://github.com/Luchenstein1625/sistemas_bioinspirados_capstone_ga.git
cd sistemas_bioinspirados_capstone_ga
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run_full_flow.ps1
```

## Ejecución completa en Linux/macOS

```bash
git clone https://github.com/Luchenstein1625/sistemas_bioinspirados_capstone_ga.git
cd sistemas_bioinspirados_capstone_ga
chmod +x scripts/run_full_flow.sh
./scripts/run_full_flow.sh
```

## Validación por etapas

```powershell
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v

capstone-portfolio-ga --recommendations data/layered_recommendations.csv --history data/resultadoPruebasGatling.txt --budget 20 --output-dir results

capstone-portfolio-aco --portfolio results/selected_validation_portfolio.csv --output-dir results/aco

python scripts/validate_outputs.py --ga-dir results --aco-dir results/aco --budget 20
```

## Evidencias esperadas

La etapa AG mantiene sus archivos actuales. La carpeta `results/aco/` agrega:

- `aco_execution_plan.csv`: los mismos 20 casos, ahora con orden de ejecución;
- `aco_best_solution.json`: score y componentes de la mejor secuencia;
- `aco_methodology.json`: parámetros, pesos y advertencias;
- `aco_history.csv` y `aco_convergence.svg`: convergencia;
- `aco_independent_runs.csv`: estabilidad multisemilla;
- `aco_comparison.csv`: ACO frente a aleatorio y dos órdenes greedy.

El validador debe finalizar con `OK`. Esto prueba reproducibilidad, integridad y
comparación offline. No prueba que el upgrade sea seguro: esa conclusión exige
aprobar la cartera, ejecutar Gatling y comprobar el contrato online del Capstone.
