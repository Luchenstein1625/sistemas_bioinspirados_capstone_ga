"""Carga y depuración de candidatos `upgrade` para el optimizador genético.

Combina dos fuentes:
  - `layered_recommendations.csv`: salida de `pde evaluate-complete` (Capstone
    Gatling AI Performance Copilot) con la recomendación por build/cuadrante.
  - `resultadoPruebasGatling.txt`: histórico corporativo de ancho fijo con la
    evidencia real de ejecuciones Gatling (Estado, errorCount, p95, etc.).

Solo sobreviven al filtro los candidatos con `action=upgrade`,
`online_validation_status=pending_new_execution`, evidencia histórica
`Estado=Success`, `Performance=1`, `errorCount=0` y `0 < p95 <= 1500 ms`.
Estas condiciones son restricciones duras de factibilidad, no ponderaciones
del fitness: un caso que no las cumple nunca entra al universo de búsqueda
del algoritmo genético.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Candidate:
    """Un candidato `upgrade` factible, con su evidencia histórica asociada."""

    index: int
    build_id: str
    pilar: str
    component: str
    method: str
    current_quadrant: str
    proposed_quadrant: str
    proposed_concurrency: str
    proposed_iterations: str
    proposed_response_time: str
    status: str
    performance: str
    error_count: float
    p95_ms: float

    @property
    def configuration(self) -> tuple[str, str, str]:
        return (
            self.proposed_concurrency,
            self.proposed_iterations,
            self.proposed_response_time,
        )

    @property
    def historical_quality(self) -> float:
        """Proxy de calidad histórica en [0,1]: combina estado, errores y p95.

        No es una probabilidad de éxito calibrada ni un costo económico
        observado; es un supuesto académico explícito, tal como se declara en
        la Discusión y en `methodology.json`.
        """
        status_score = 1.0 if self.status.lower() == "success" else 0.0
        error_score = 1.0 if self.error_count == 0 else max(0.0, 1.0 - self.error_count / 10.0)
        latency_score = max(0.0, min(1.0, 1.0 - self.p95_ms / 3_000.0))
        return 0.35 * status_score + 0.40 * error_score + 0.25 * latency_score


def read_fixed_width(path: Path) -> list[dict[str, str]]:
    """Lee el histórico de ancho fijo usando la fila de guiones como layout."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    spans = [match.span() for match in re.finditer(r"-+", lines[1])]
    names = [lines[0][start:end].strip() for start, end in spans]
    rows = []
    for line in lines[2:]:
        if line.strip():
            rows.append({name: line[start:end].strip() for name, (start, end) in zip(names, spans)})
    return rows


def number(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_candidates(recommendations_path: Path, history_path: Path) -> list[Candidate]:
    """Integra recomendaciones + histórico, aplica restricciones duras y
    elimina duplicados por (build_id, cuadrante propuesto, configuración
    propuesta). Retorna solo candidatos `upgrade` pendientes y seguros."""
    history = read_fixed_width(history_path)
    by_build: dict[str, list[dict[str, str]]] = {}
    for row in history:
        by_build.setdefault(row.get("Build_Id", ""), []).append(row)

    with recommendations_path.open(encoding="utf-8", newline="") as stream:
        recommendations = list(csv.DictReader(stream))

    candidates = []
    seen = set()
    for recommendation in recommendations:
        if recommendation.get("action") != "upgrade":
            continue
        if recommendation.get("online_validation_status") != "pending_new_execution":
            continue
        build_id = recommendation.get("build_id", "")
        matches = by_build.get(build_id, [])
        safe_matches = [
            row
            for row in matches
            if row.get("Estado", "").strip().lower() == "success"
            and row.get("Performance", "").strip() == "1"
            and number(row.get("errorCount", ""), -1) == 0
            and 0 < number(row.get("p95", ""), -1) <= 1_500
        ]
        # Operational safety is a hard feasibility constraint, not a fitness weight.
        if not safe_matches:
            continue
        evidence = min(
            safe_matches,
            key=lambda row: (
                number(row.get("errorCount", ""), 10_000),
                number(row.get("p95", ""), 10_000_000),
            ),
            default={},
        )
        key = (
            build_id,
            recommendation.get("proposed_quadrant", ""),
            recommendation.get("proposed_concurrency", ""),
            recommendation.get("proposed_iterations", ""),
            recommendation.get("proposed_response_time", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            Candidate(
                index=len(candidates),
                build_id=build_id,
                pilar=evidence.get("pilar", "unknown") or "unknown",
                component=evidence.get("Tcomponente", "unknown") or "unknown",
                method=evidence.get("Metodo", "unknown") or "unknown",
                current_quadrant=recommendation.get("current_quadrant", ""),
                proposed_quadrant=recommendation.get("proposed_quadrant", ""),
                proposed_concurrency=recommendation.get("proposed_concurrency", ""),
                proposed_iterations=recommendation.get("proposed_iterations", ""),
                proposed_response_time=recommendation.get("proposed_response_time", ""),
                status=evidence.get("Estado", "unknown"),
                performance=evidence.get("Performance", ""),
                error_count=number(evidence.get("errorCount", ""), 10_000),
                p95_ms=number(evidence.get("p95", ""), 10_000_000),
            )
        )
    if not candidates:
        raise ValueError("No pending upgrade candidates were found.")
    return candidates
