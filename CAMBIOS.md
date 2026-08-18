# Delta AG + ACO

Copiar el contenido de esta carpeta sobre la raíz del repositorio
`sistemas_bioinspirados_capstone_ga`.

## Archivos modificados

- `README.md`
- `pyproject.toml`

## Archivos nuevos

- `src/validation_portfolio/aco.py`
- `src/validation_portfolio/aco_cli.py`
- `tests/test_aco.py`
- `scripts/validate_outputs.py`
- `scripts/run_full_flow.ps1`
- `scripts/run_full_flow.sh`
- `docs/VALIDACION_AG_ACO.md`

## Archivos que no se reemplazan

No se incluyen ni modifican los datasets, resultados anteriores, documentos
PDF ni los módulos actuales `data.py`, `genetic.py` y `cli.py`.

## Validación realizada

- Instalación editable del paquete: correcta.
- Cinco pruebas unitarias: correctas.
- Ejecución AG con 113 candidatos y presupuesto 20: correcta.
- Ejecución ACO con 10 semillas: correcta.
- Integridad de cartera AG/ACO y restricciones duras: correcta.
- Estado final conservado: `pending_new_execution`.

Resultado ACO observado en la validación local:

| Método | Score |
| --- | ---: |
| Orden por calidad | 0,54056155 |
| Promedio aleatorio | 0,59608790 |
| Greedy de transición | 0,71077730 |
| ACO | 0,74878943 |

Estos scores corresponden a proxies offline. La aceptación de los upgrades
requiere aprobación humana y nuevas ejecuciones Gatling.

