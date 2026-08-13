# Optimizador genético de cartera de validación Gatling

Proyecto para **15 Sistemas Bioinspirados - MIA 2026**, integrado conceptualmente con **Gatling AI Performance Copilot v1.6.0**.

## Problema real abordado

El Capstone ya contiene cuatro capas:

1. aplicabilidad (`applies/not_applies`);
2. decisión (`review/maintain/upgrade`);
3. propuesta controlada de parámetros;
4. evaluación offline y contrato de validación online.

La salida actual contiene propuestas `upgrade` con estado `pending_new_execution`. En la ejecución analizada existen **275 candidatos**, pero el proyecto no decide cuáles validar primero cuando el tiempo o presupuesto de pruebas es limitado.

Este proyecto utiliza un algoritmo genético para seleccionar una cartera de casos que maximice simultáneamente:

- diversidad de pilares, componentes y cuadrantes;
- evidencia histórica favorable;
- cobertura de diferentes configuraciones;
- eficiencia del presupuesto;

y penalice selecciones redundantes o riesgosas.

El algoritmo **no ejecuta Gatling ni aprueba upgrades**. Entrega un orden experimental para revisión humana.

## Entradas

- `data/layered_recommendations.csv`: salida real de `pde evaluate-complete`.
- `data/resultadoPruebasGatling.txt`: histórico corporativo utilizado por el Capstone.

## Ejecución

No requiere dependencias externas; utiliza Python 3.11 o superior.

```powershell
cd sistemas_bioinspirados_capstone_ga
python -m pip install -e .
capstone-portfolio-ga `
  --recommendations data/layered_recommendations.csv `
  --history data/resultadoPruebasGatling.txt `
  --budget 20 `
  --output-dir results
```

Sin instalar:

```powershell
$env:PYTHONPATH="src"
python -m validation_portfolio.cli `
  --recommendations data/layered_recommendations.csv `
  --history data/resultadoPruebasGatling.txt `
  --budget 20 `
  --output-dir results
```

## Cromosoma

Cada gen binario representa un candidato `upgrade`:

```text
[0, 1, 0, 0, 1, ...]
```

- `1`: incluir en la campaña de validación.
- `0`: dejar para una campaña posterior.

El cromosoma se repara para contener exactamente el número de casos definido por `--budget`.

Antes de crear la población se aplica una restricción dura de seguridad. Solo son factibles
los casos con `Estado=Success`, `Performance=1`, `errorCount=0` y p95 válido menor o igual
a 1.500 ms. Un caso fallido no puede compensar su riesgo obteniendo diversidad en el fitness.

## Fitness

```text
fitness = 0,30 × diversidad de pilar
        + 0,20 × diversidad de componente
        + 0,15 × diversidad de cuadrante
        + 0,20 × calidad histórica
        + 0,10 × diversidad de configuración
        + 0,05 × cobertura de builds
        - penalización por redundancia
```

La calidad histórica usa `Estado`, errores y p95. Los pesos son supuestos académicos configurables, no costos bancarios demostrados.

## Salidas

- `selected_validation_portfolio.csv`: cartera priorizada.
- `best_solution.json`: cromosoma, fitness y cobertura.
- `fitness_history.csv`: evolución generacional.
- `fitness_evolution.svg`: gráfico de convergencia.
- `comparison.csv`: algoritmo genético frente a selección aleatoria y greedy.
- `methodology.json`: trazabilidad de fórmula, restricciones y semillas.

## Relación con el Capstone

Este proyecto no duplica el modelo Random Forest, el análisis de umbrales ni la recomendación por pares. Actúa después de la capa 4 y ayuda a diseñar la muestra de validación experimental que actualmente está pendiente.
