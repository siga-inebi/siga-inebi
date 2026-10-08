#!/usr/bin/env python3
"""Generate reproducible Phase 7 requirement and validation snapshots."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "docs/requirements/requirements.json"
CATALOGUE = ROOT / "docs/requirements/requirements-catalogue.md"
OUTPUT = ROOT / "docs/quality/fase-7"


def catalogue_statuses() -> dict[str, str]:
    statuses: dict[str, str] = {}
    for line in CATALOGUE.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| RF-") and not line.startswith("| RNF-"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) >= 5:
            statuses.setdefault(cells[0], cells[4])
    return statuses


def scope_for(requirement_id: str, implementation_status: str) -> tuple[str, str]:
    if requirement_id in {"RNF-REN-003", "RNF-REN-004"}:
        return "Diferido", "ADR-0009: procesamiento trabajador diferido; requiere decision posterior."
    if implementation_status == "Implemented":
        return "Incluido para validacion", "Implementado segun catalogo; falta ejecutar evidencia sobre SHA candidato."
    if implementation_status in {"In Progress", "Under Review"}:
        return "Incluido condicionado", "Requiere cerrar brecha y ejecutar evidencia antes de aceptacion."
    if implementation_status == "Not implemented":
        return "Fuera del candidato actual", "No implementado segun catalogo; requiere aprobacion explicita si se pretende excluir."
    if implementation_status == "Deferred":
        return "Diferido", "Diferido en catalogo; conservar decision y no contarlo como aprobado."
    return "Pendiente de clasificacion", "No se encontro estado confiable en catalogo; revisar en D1."


def main() -> None:
    requirements = json.loads(REQUIREMENTS.read_text(encoding="utf-8"))
    statuses = catalogue_statuses()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    catalog_path = OUTPUT / "catalogo-casos.csv"
    matrix_path = OUTPUT / "matriz-final.csv"

    catalog_fields = [
        "requirement_id", "kind", "priority", "domain", "module",
        "acceptance_criteria", "implementation_status_source", "scope_classification",
        "scope_rationale", "case_id", "test_reference", "execution_id",
        "validation_result", "evidence", "incident", "owner", "reviewer", "notes",
    ]
    matrix_fields = [
        "requirement_id", "kind", "priority", "acceptance_criteria", "scope_classification",
        "implementation_status_source", "issue", "design_adr", "code", "test_reference",
        "pull_request", "candidate_sha", "execution_id", "validation_result", "evidence",
        "incident", "owner", "reviewer", "exclusion_decision", "notes",
    ]

    counts: Counter[str] = Counter()
    with catalog_path.open("w", encoding="utf-8", newline="") as catalog_file, matrix_path.open(
        "w", encoding="utf-8", newline=""
    ) as matrix_file:
        catalog = csv.DictWriter(catalog_file, fieldnames=catalog_fields)
        matrix = csv.DictWriter(matrix_file, fieldnames=matrix_fields)
        catalog.writeheader()
        matrix.writeheader()
        for requirement in sorted(requirements, key=lambda item: item["id"]):
            requirement_id = requirement["id"]
            implementation_status = statuses.get(requirement_id, "No localizado")
            scope, rationale = scope_for(requirement_id, implementation_status)
            counts[scope] += 1
            common = {
                "requirement_id": requirement_id,
                "kind": requirement["kind"],
                "priority": requirement["priority"],
                "acceptance_criteria": requirement["acceptance_criteria"],
                "scope_classification": scope,
                "implementation_status_source": implementation_status,
            }
            catalog.writerow(
                {
                    **common,
                    "domain": requirement["domain"],
                    "module": requirement["module"],
                    "scope_rationale": rationale,
                    "case_id": "",
                    "test_reference": "",
                    "execution_id": "",
                    "validation_result": "No ejecutado",
                    "evidence": "",
                    "incident": "",
                    "owner": "Pablo (coordinacion); responsable de dominio pendiente",
                    "reviewer": "",
                    "notes": "Generado desde requirements.json y requirements-catalogue.md; actualizar tras D1.",
                }
            )
            matrix.writerow(
                {
                    **common,
                    "issue": "",
                    "design_adr": "",
                    "code": "",
                    "test_reference": "",
                    "pull_request": "",
                    "candidate_sha": "",
                    "execution_id": "",
                    "validation_result": "No ejecutado",
                    "evidence": "",
                    "incident": "",
                    "owner": "Pablo (coordinacion); responsable de dominio pendiente",
                    "reviewer": "",
                    "exclusion_decision": "",
                    "notes": rationale,
                }
            )

    print(f"Generated {len(requirements)} requirement rows.")
    for scope, count in sorted(counts.items()):
        print(f"{scope}: {count}")


if __name__ == "__main__":
    main()
