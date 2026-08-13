# Informe de avance

## Selección bioinspirada de una cartera de validación para Gatling AI Performance Copilot

**Asignatura:** Sistemas Bioinspirados - MIA 2026  
**Profesor:** Ricardo Contreras A.  
**Integrantes:** Luis Araya, Rodrigo González, Hernán Medina  
**Fecha:** 31 de agosto de 2026

## 1. Introducción

Gatling AI Performance Copilot automatiza el análisis de resultados históricos y genera recomendaciones `review`, `maintain` o `upgrade`. Su versión actual posee cuatro capas: aplicabilidad, decisión, propuesta de parámetros y validación. Las propuestas `upgrade` no modifican automáticamente una prueba; permanecen pendientes hasta contar con aprobación humana y una nueva ejecución Gatling.

La ejecución completa analizada produjo 275 propuestas `upgrade` pendientes. Validarlas todas simultáneamente puede exceder el tiempo y capacidad disponibles. El problema abordado consiste en elegir una muestra pequeña, diversa y respaldada por evidencia para una primera campaña experimental.

## 2. Justificación

Una selección manual podría concentrarse en un mismo pilar, componente, build o cuadrante y entregar evidencia poco representativa. El algoritmo genético permite explorar combinaciones de candidatos y equilibrar objetivos contrapuestos: diversidad, calidad histórica, cobertura y redundancia.

La solución complementa el Capstone sin repetir su clasificación, comparación de modelos, optimización de umbrales ni recomendación por pares. Opera después de la capa 4 y ayuda a planificar la evidencia que el proyecto declara pendiente.

## 3. Representación

Cada cromosoma es un vector binario de longitud igual al número de propuestas únicas. Un valor 1 incorpora el candidato y un valor 0 lo excluye. Todos los cromosomas se reparan para respetar exactamente el presupuesto experimental, inicialmente 20 casos.

Antes de la optimización se aplica una restricción de factibilidad: solo ingresan casos con estado exitoso, `Performance=1`, cero errores y p95 válido menor o igual a 1.500 ms. Esta condición es una regla de seguridad y no un peso del fitness.

## 4. Fitness

```text
fitness = 0,30 × cobertura de pilares
        + 0,20 × cobertura de componentes
        + 0,15 × cobertura de cuadrantes
        + 0,20 × calidad histórica
        + 0,10 × diversidad de configuraciones
        + 0,05 × cobertura de builds
        - 0,10 × redundancia
```

La calidad histórica combina estado exitoso, ausencia de errores y margen de p95. Los pesos son supuestos académicos explícitos y ajustables; no representan costos económicos demostrados.

## 5. Operadores

- Población inicial: carteras aleatorias válidas.
- Selección: torneo de cuatro individuos.
- Cruzamiento: uniforme.
- Mutación: inversión de bits.
- Reparación: agrega o elimina candidatos hasta respetar el presupuesto.
- Reemplazo: elitismo más descendencia.
- Término: 120 generaciones.

## 6. Pseudocódigo

```text
leer recomendaciones y conservar upgrades pendientes
unir cada propuesta con evidencia histórica por Build_Id
eliminar propuestas duplicadas
crear población de carteras aleatorias de tamaño presupuesto

para cada generación:
    evaluar diversidad, calidad, cobertura y redundancia
    conservar elite
    seleccionar padres por torneo
    cruzar cromosomas
    mutar genes
    reparar presupuesto
    formar nueva población

retornar la mejor cartera
comparar contra selección aleatoria y greedy
mantener aprobación humana y estado pending_new_execution
```

## 7. Resultados esperados

Se espera que la cartera genética obtenga mayor fitness que el promedio de 100 muestras aleatorias y que una heurística greedy basada solamente en calidad. La salida debe cubrir más pilares, componentes y cuadrantes sin incluir ejecuciones fallidas o con errores conocidos.

## 8. Validación final pendiente

El fitness permite priorizar la campaña, pero no demuestra que un `upgrade` sea seguro. Cada caso seleccionado debe ser aprobado por un especialista, ejecutado nuevamente en Gatling y contrastado con `errorCount`, p95, RPS, `successCount` y `Estado`, según el contrato del Capstone.

## 9. Referencias preliminares

- Holland, J. H. (1975). *Adaptation in Natural and Artificial Systems*.
- Goldberg, D. E. (1989). *Genetic Algorithms in Search, Optimization, and Machine Learning*.
- Eiben, A. E., & Smith, J. E. (2015). *Introduction to Evolutionary Computing*.
