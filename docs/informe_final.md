# Informe final

## Selección bioinspirada de una cartera de validación para Gatling AI Performance Copilot

**Asignatura:** Sistemas Bioinspirados - MIA 2026  
**Integrantes:** [Completar]  
**Fecha:** 14 de septiembre de 2026

## Resumen

Se desarrolló un algoritmo genético para seleccionar, bajo un presupuesto limitado, los casos `upgrade` que conviene priorizar en la validación experimental del Capstone. El pipeline completo había generado 275 propuestas pendientes. Después de eliminar duplicados por build, cuadrante y configuración, se obtuvieron 113 candidatos únicos. El algoritmo seleccionó una cartera de 20 casos y fue comparado con selección aleatoria y una heurística greedy.

## Resultados

En diez ejecuciones independientes, el mejor fitness fue 0,99026833, el promedio fue 0,98370833 y la desviación estándar fue 0,00294566. El promedio de 100 carteras aleatorias fue 0,75951683 y la heurística greedy alcanzó 0,46132060. La cartera genética seleccionada cubrió:

- 20 builds diferentes;
- 4 pilares;
- 12 componentes;
- 7 cuadrantes;
- 20 configuraciones distintas;
- cero ejecuciones históricas fallidas;
- cero casos con errores históricos.

El p95 de los casos seleccionados se ubicó entre 386 y 1.125 ms. Todos los casos cumplen `Estado=Success`, `Performance=1` y `errorCount=0`. Estas condiciones se implementaron como restricciones duras, por lo que un caso fallido no puede compensar el riesgo mediante una mayor diversidad. El estado de todos los casos permanece `pending_new_execution` y cada selección requiere revisión humana.

## Discusión

La diferencia respecto del greedy muestra que elegir únicamente los casos históricamente más favorables produce una cartera redundante. La función genética sacrifica una fracción de calidad individual para cubrir más pilares, componentes, configuraciones y cuadrantes. Esta propiedad es relevante porque la finalidad de la campaña no es solo maximizar la probabilidad de éxito, sino producir evidencia útil sobre diferentes contextos operacionales.

La comparación con carteras aleatorias indica que la búsqueda evolutiva identifica combinaciones de mayor cobertura y menor redundancia. Sin embargo, el fitness no equivale a desempeño real de Gatling. La calidad histórica es un proxy construido desde estado, errores y p95. Tampoco se dispone todavía de costos monetarios observados para definir pesos económicamente óptimos.

El aporte se ubica después de las cuatro capas existentes del Capstone. No modifica la clasificación de aplicabilidad, la política `review/maintain/upgrade`, el análisis de umbrales ni la recomendación por pares. Su función es priorizar la muestra experimental necesaria para cerrar el pendiente de validación online.

## Conclusiones

El algoritmo genético resolvió satisfactoriamente el problema de seleccionar una cartera diversa bajo una restricción de presupuesto. La solución superó a los comparadores offline y mantuvo las restricciones de seguridad definidas. El resultado demuestra la utilidad de los algoritmos bioinspirados para optimización combinatoria aplicada a planificación de experimentos.

No puede afirmarse todavía que los upgrades seleccionados sean seguros. La conclusión operacional depende de ejecutar cada propuesta en Gatling, verificar cero errores, estado exitoso y ausencia de regresión en p95, RPS y solicitudes exitosas. Como trabajo futuro se propone aprender los pesos desde costos observados y realimentar el fitness con los resultados online.

## Referencias

- Holland, J. H. (1975). *Adaptation in Natural and Artificial Systems*. University of Michigan Press.
- Goldberg, D. E. (1989). *Genetic Algorithms in Search, Optimization, and Machine Learning*. Addison-Wesley.
- Eiben, A. E., & Smith, J. E. (2015). *Introduction to Evolutionary Computing*. Springer.
- Deb, K. (2001). *Multi-Objective Optimization Using Evolutionary Algorithms*. Wiley.
