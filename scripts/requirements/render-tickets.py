#!/usr/bin/env python3
"""Render one issue body per requirement, plus the seven epic bodies.

    python3 scripts/requirements/render-tickets.py
    python3 scripts/requirements/render-tickets.py --refresh-epics out/created.tsv

Functional requirements follow the section layout of
`.github/ISSUE_TEMPLATE/feature.yml`; non-functional ones follow
`.github/ISSUE_TEMPLATE/technical-task.yml`. Bodies created through the API skip
the issue forms, so mirroring the sections by hand is what keeps a generated
ticket readable next to a hand-filed one.

Each ticket body carries a `{{EPIC}}` placeholder that `create-issues.sh`
replaces with the epic's real issue number at creation time.

`--refresh-epics` re-renders the epic bodies with a task list of the children
that were actually created, so an epic shows live progress on the board.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import implementation  # noqa: E402
import mapping  # noqa: E402
import parser as cards_parser  # noqa: E402
import scenarios as scenarios_module  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_OUT = os.path.join(HERE, "out")
DEFAULT_SPECS = os.path.join(REPO_ROOT, "docs", "requirements", "openspec")
CATALOGUE = os.path.join(REPO_ROOT, "docs", "requirements", "requirements-catalogue.md")
DEFAULT_REQUIREMENTS = os.path.join(
    REPO_ROOT, "docs", "requirements", "requirements.json"
)

EPIC_PLACEHOLDER = "{{EPIC}}"

PROVENANCE = (
    "Generado desde la matriz de trazabilidad de `INEBI Fase 2.pdf` con "
    "`scripts/requirements/`. Al cerrar este issue, actualizar "
    "`docs/requirements/traceability-matrix.md`."
)

NO_CRITERION_NOTICE = (
    "**El documento fuente no define un criterio de aceptacion para este "
    "requerimiento.** No hay ficha para este ID en la matriz de trazabilidad del "
    "PDF. Definir el criterio antes de empezar; por eso el issue esta etiquetado "
    "`status:blocked`."
)

SECURITY_NOTICE = (
    "Dominio sensible (`{domain}`): la implementacion debe respetar el control de "
    "acceso por rol y alcance, y registrar la operacion en bitacora."
)


def _value_or_tbd(value):
    return value if value else "TBD"


def _requirement_line(record):
    return (
        f"`{record['id']}` — {record['catalogue_description']} "
        f"(prioridad MoSCoW: {record['priority']})"
    )


def _dependencies(record):
    lines = [f"- Epica: {EPIC_PLACEHOLDER}"]
    if record["user_story"]:
        lines.append(f"- Historia de usuario: {record['user_story']}")
    if record["business_rule"]:
        lines.append(f"- Regla de negocio: {record['business_rule']}")
    if not record["user_story"] and not record["business_rule"]:
        lines.append("- Sin historia de usuario ni regla de negocio declaradas.")
    return "\n".join(lines)


def _criteria_block(record):
    """Acceptance criterion, followed by the behavioural scenarios when they exist."""
    spec = record.get("spec")
    parts = []

    if record["acceptance_criteria"]:
        parts.append(record["acceptance_criteria"])
    elif spec:
        parts.append(
            "El documento de requerimientos no trae criterio para este ID; el "
            "comportamiento exigible es el de la especificacion de capacidad:"
        )
    else:
        parts.append(NO_CRITERION_NOTICE)

    if spec:
        parts.append("")
        parts.append(f"### Comportamiento exigido\n\n{spec['statement']}")
        if spec["scenarios"]:
            parts.append("")
            parts.append("### Escenarios verificables")
            for index, scenario in enumerate(spec["scenarios"], 1):
                parts.append("")
                parts.append(f"**Escenario {index}: {scenario['title']}**")
                parts.append("")
                parts.extend(f"- {step}" for step in scenario["steps"])
        parts.append("")
        parts.append(f"Fuente: `{spec['source']}` (capacidad `{spec['capability']}`).")

    return "\n".join(parts)


def _implementation_block(record):
    """The "what am I expected to program" section, grounded in the repo layout."""
    domain = record["domain"]
    area_label = mapping.area_label_for(domain, record.get("prefix"))
    info = implementation.domain_info(domain)

    lines = [implementation.app_status_note(domain), ""]

    backend = implementation.backend_paths(domain)
    if backend:
        lines.append("Capas que toca este requerimiento:")
        lines.append("")
        lines.extend(f"- `{path}` — {why}" for path, why in backend)
        lines.append("")

    frontend = implementation.frontend_paths(domain, area_label)
    if frontend:
        lines.append("Cliente web:")
        lines.append("")
        lines.extend(f"- `{path}` — {why}" for path, why in frontend)
        lines.append("")

    if info["depends_on"]:
        lines.append(
            "Depende de que estos dominios ya funcionen: "
            + ", ".join(f"`{d}`" for d in info["depends_on"])
            + "."
        )
        lines.append("")

    docs = info["design_docs"] + ["docs/architecture/api-conventions.md"]
    lines.append("Leer antes de programar:")
    lines.append("")
    lines.extend(f"- `{doc}`" for doc in dict.fromkeys(docs))

    return "\n".join(lines).rstrip()


def _tests_block(record, kind):
    """Name the test files and, when scenarios exist, the cases to write."""
    domain = record["domain"]
    area_label = mapping.area_label_for(domain, record.get("prefix"))
    paths = implementation.test_paths(domain, area_label)
    spec = record.get("spec")

    lines = []
    if paths:
        lines.append("Archivos de prueba que deben existir:")
        lines.append("")
        lines.extend(f"- `{path}` — {why}" for path, why in paths)
        lines.append("")

    if spec and spec["scenarios"]:
        lines.append(
            f"Un caso de prueba por escenario ({len(spec['scenarios'])} en total):"
        )
        lines.append("")
        lines.extend(
            f"- [ ] {scenario['title']}" for scenario in spec["scenarios"]
        )
        lines.append("")
        lines.append(
            "El `THEN` de cada escenario es la asercion. Un escenario sin prueba "
            "es un escenario no implementado."
        )
    else:
        lines.append(
            "**Sin escenarios en la fuente**: derivar los casos del criterio de "
            "aceptacion y dejarlos escritos en este issue antes de programar. "
            "Como minimo, el camino feliz y el rechazo por autorizacion."
        )

    lines.append("")
    lines.append(
        "Correr con `make test-backend`. Sin prueba verificable el requerimiento "
        "no se marca `Implemented` (AGENTS.md regla 11)."
    )
    return "\n".join(lines)


def _security_block(record):
    if mapping.area_label_for(record["domain"]) == "area:security":
        return SECURITY_NOTICE.format(domain=record["domain"])
    return "Sin requisitos de autorizacion adicionales a los del dominio."


def render_functional(record):
    """Body for an RF, mirroring .github/ISSUE_TEMPLATE/feature.yml."""
    module = record["module"] or "sin modulo declarado"
    return f"""## Necesidad

{record['name']}.

Modulo del sistema: {module}.

## Usuario o rol principal

{_value_or_tbd(record['actor'])}

## Requerimientos RF o RNF

{_requirement_line(record)}

## Criterios de aceptacion

{_criteria_block(record)}

## Que se espera programar

{_implementation_block(record)}

## Dependencias

{_dependencies(record)}

## Datos involucrados

Dominio: `{record['domain']}` — {implementation.domain_info(record['domain'])['responsibility'] or 'sin responsabilidad declarada en el domain map'}.

## Seguridad y autorizacion

{_security_block(record)}

## Pruebas esperadas

{_tests_block(record, 'RF')}

## Fuera de alcance

Todo lo que no sea `{record['id']}`. Si al implementar aparece comportamiento que
este requerimiento no declara, abrir otro issue y citarlo aqui; no ampliar el
alcance en silencio (AGENTS.md regla 2).

---

{PROVENANCE}
"""


def render_non_functional(record):
    """Body for an RNF, mirroring .github/ISSUE_TEMPLATE/technical-task.yml."""
    module = record["module"] or "sin modulo declarado"
    return f"""## Objetivo

{record['name']}.

Modulo del sistema: {module}.

## Justificacion

Requerimiento no funcional del catalogo institucional.

{_requirement_line(record)}

Rol o actor afectado: {_value_or_tbd(record['actor'])}.

## Alcance

Dominio: `{record['domain']}` — {implementation.domain_info(record['domain'])['responsibility'] or 'sin responsabilidad declarada en el domain map'}.

{_dependencies(record)}

### Que se espera programar

{_implementation_block(record)}

## Criterios de finalizacion

{_criteria_block(record)}

## Riesgos

{_security_block(record)}

## Validaciones

{_tests_block(record, 'RNF')}

---

{PROVENANCE}
"""


def render_epic(epic, members, created=None):
    """Body for an epic. `created` maps requirement id -> issue number."""
    lines = [
        "## Objetivo",
        "",
        epic["summary"],
        "",
        f"Prioridad global declarada en la lista priorizada de funcionalidades: "
        f"**{epic['priority']}**.",
        "",
        "## Justificacion",
        "",
        f"Agrupa los {len(members)} requerimientos de este modulo para dar "
        "seguimiento conjunto en el tablero.",
        "",
        "## Alcance",
        "",
    ]

    for record in members:
        if created and record["id"] in created:
            lines.append(
                f"- [ ] #{created[record['id']]} — `{record['id']}` {record['name']}"
            )
        else:
            lines.append(f"- [ ] `{record['id']}` {record['name']}")

    must = sum(1 for r in members if r["priority"] == "Debe")
    blocked = sum(1 for r in members if not r["acceptance_criteria"])
    lines += [
        "",
        "## Criterios de finalizacion",
        "",
        f"Los {len(members)} issues de la lista estan cerrados, de los cuales "
        f"{must} son de prioridad `Debe`.",
    ]
    if blocked:
        lines.append(
            f"\n{blocked} de ellos no tienen criterio de aceptacion en el documento "
            "fuente y estan etiquetados `status:blocked`."
        )
    lines += ["", "---", "", PROVENANCE, ""]
    return "\n".join(lines)


def load_created(path):
    """Read out/created.tsv into {requirement_id: issue_number}."""
    created = {}
    if not os.path.exists(path):
        return created
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) >= 2 and fields[0] and fields[1]:
                created[fields[0]] = fields[1]
    return created


def main():
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("--out", default=DEFAULT_OUT)
    argument_parser.add_argument("--requirements", default=DEFAULT_REQUIREMENTS)
    argument_parser.add_argument("--specs-dir", default=DEFAULT_SPECS)
    argument_parser.add_argument(
        "--refresh-epics",
        metavar="CREATED_TSV",
        help="only re-render epic bodies, filling in child issue numbers",
    )
    args = argument_parser.parse_args()

    requirements_path = args.requirements
    if not os.path.exists(requirements_path):
        sys.exit(
            f"ERROR: {requirements_path} not found. "
            "It should be versioned; regenerate it with "
            "scripts/requirements/extract-requirements.py (needs the source PDF)."
        )
    with open(requirements_path, encoding="utf-8") as handle:
        records = json.load(handle)

    # Attach the behavioural specs. Absent capability specs are not an error:
    # ten prefixes and every RNF simply have no such source.
    with open(CATALOGUE, encoding="utf-8") as handle:
        catalogue = cards_parser.parse_catalogue(handle.read())
    specs, unmatched = scenarios_module.load(
        args.specs_dir, catalogue, cards_parser.normalise
    )
    for record in records:
        record["spec"] = specs.get(record["id"])
    if unmatched:
        print(
            f"WARNING: {len(unmatched)} spec requirements matched no catalogue ID:"
        )
        for capability, title in unmatched:
            print(f"  {capability}: {title}")

    epics_dir = os.path.join(args.out, "epics")
    tickets_dir = os.path.join(args.out, "tickets")
    os.makedirs(epics_dir, exist_ok=True)

    created = load_created(args.refresh_epics) if args.refresh_epics else None

    epic_rows = []
    for epic in mapping.EPICS:
        members = [r for r in records if r["epic"] == epic["key"]]
        members.sort(key=lambda r: r["id"])
        path = os.path.join(epics_dir, f"{epic['key']}.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(render_epic(epic, members, created))
        epic_rows.append(
            "\t".join(
                [
                    f"epic:{epic['key']}",
                    mapping.epic_title_for(epic),
                    ",".join(mapping.epic_labels_for(epic)),
                    path,
                ]
            )
        )

    with open(os.path.join(args.out, "epics.tsv"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(epic_rows) + "\n")

    if args.refresh_epics:
        # Count requirements only: created.tsv also carries the epic rows.
        filled = sum(1 for r in records if r["id"] in (created or {}))
        print(f"Re-rendered {len(mapping.EPICS)} epic bodies with {filled} children.")
        return

    os.makedirs(tickets_dir, exist_ok=True)
    for record in records:
        body = (
            render_functional(record)
            if record["kind"] == "RF"
            else render_non_functional(record)
        )
        with open(os.path.join(tickets_dir, f"{record['id']}.md"), "w", encoding="utf-8") as handle:
            handle.write(body)

    index_path = os.path.join(args.out, "tickets.tsv")
    with open(index_path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                "\t".join(
                    [
                        record["id"],
                        record["epic"],
                        mapping.title_for(record),
                        ",".join(mapping.labels_for(record)),
                        os.path.join(tickets_dir, f"{record['id']}.md"),
                    ]
                )
                + "\n"
            )

    with_scenarios = sum(1 for r in records if r.get("spec"))
    scenario_count = sum(len(r["spec"]["scenarios"]) for r in records if r.get("spec"))
    print(f"Rendered {len(records)} ticket bodies into {tickets_dir}")
    print(
        f"  with behavioural scenarios: {with_scenarios} "
        f"({scenario_count} escenarios en total)"
    )
    print(f"  without any scenario source: {len(records) - with_scenarios}")
    print(f"Rendered {len(mapping.EPICS)} epic bodies into {epics_dir}")
    print(f"Wrote the creation index to {index_path}")


if __name__ == "__main__":
    main()
