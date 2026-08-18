# Optimización bioinspirada de validación Gatling: AG + ACO

Proyecto para **15 Sistemas Bioinspirados - MIA 2026**, integrado
conceptualmente con **Gatling AI Performance Copilot v1.6.0**.

## Problema abordado

El Capstone ya contiene cuatro capas: aplicabilidad, decisión
`review/maintain/upgrade`, propuesta controlada de parámetros y evaluación
offline con contrato de validación online. En la ejecución analizada generó 275
propuestas `upgrade` pendientes; después de integrar el histórico, aplicar las
restricciones duras y eliminar duplicados quedaron 113 candidatos factibles.

El flujo híbrido divide el problema en dos decisiones:

1. **Algoritmo genético (AG):** selecciona qué 20 casos validar.
2. **Optimización por colonia de hormigas (ACO):** ordena esos mismos 20 casos.

Ningún algoritmo ejecuta Gatling ni aprueba upgrades. El resultado permanece
`pending_new_execution` y requiere revisión humana.

## Entradas

- `data/layered_recommendations.csv`: salida de `pde evaluate-complete`.
- `data/resultadoPruebasGatling.txt`: histórico corporativo.

## Flujo completo

### Windows PowerShell

```powershell
git clone https://github.com/Luchenstein1625/sistemas_bioinspirados_capstone_ga.git
cd sistemas_bioinspirados_capstone_ga
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run_full_flow.ps1
```

### Linux/macOS

```bash
git clone https://github.com/Luchenstein1625/sistemas_bioinspirados_capstone_ga.git
cd sistemas_bioinspirados_capstone_ga
chmod +x scripts/run_full_flow.sh
./scripts/run_full_flow.sh
```

## Ejecución manual

```powershell
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v

capstone-portfolio-ga `
  --recommendations data/layered_recommendations.csv `
  --history data/resultadoPruebasGatling.txt `
  --budget 20 --population 80 --generations 120 --runs 10 --seed 42 `
  --output-dir results

capstone-portfolio-aco `
  --portfolio results/selected_validation_portfolio.csv `
  --ants 40 --iterations 100 --runs 10 --seed 42 --random-samples 100 `
  --output-dir results/aco

python scripts/validate_outputs.py --ga-dir results --aco-dir results/aco --budget 20
```

## Restricciones duras del AG

Solo son factibles los casos con:

- `Estado=Success`;
- `Performance=1`;
- `errorCount=0`;
- `0 < p95 <= 1500 ms`;
- `action=upgrade` y `online_validation_status=pending_new_execution`.

Estas condiciones se aplican antes del fitness: un caso inseguro no puede
compensar su riesgo aportando diversidad.

## Fitness del AG

```text
fitness = 0,30 × cobertura de pilares
        + 0,20 × cobertura de componentes
        + 0,15 × cobertura de cuadrantes
        + 0,20 × calidad histórica
        + 0,10 × diversidad de configuración
        + 0,05 × cobertura de builds
        - 0,10 × concentración máxima por build
```

## Objetivo de ACO

ACO no vuelve a seleccionar la cartera. Optimiza una permutación de los 20
casos del AG mediante:

```text
score = 0,50 × eficiencia de transición
      + 0,35 × cobertura temprana acumulada
      + 0,15 × calidad histórica temprana
```

La eficiencia de transición utiliza diferencias de configuración, cuadrante,
pilar y componente. Son **proxies académicos explícitos**, no costos monetarios
ni duraciones observadas. Cuando existan costos reales, deben reemplazar estos
proxies y repetirse la comparación.

## Comparadores

El AG se compara con 100 carteras aleatorias y greedy por calidad. ACO se
compara con:

- promedio de 100 permutaciones aleatorias;
- orden descendente por calidad histórica;
- greedy de transición;
- mejor resultado ACO de 10 semillas.

## Salidas

### AG (`results/`)

- `selected_validation_portfolio.csv`
- `best_solution.json`
- `fitness_history.csv` y `fitness_evolution.svg`
- `comparison.csv`
- `independent_runs.csv`
- `methodology.json`

### ACO (`results/aco/`)

- `aco_execution_plan.csv`
- `aco_best_solution.json`
- `aco_methodology.json`
- `aco_history.csv` y `aco_convergence.svg`
- `aco_independent_runs.csv`
- `aco_comparison.csv`

La guía detallada está en [`docs/VALIDACION_AG_ACO.md`](docs/VALIDACION_AG_ACO.md).
