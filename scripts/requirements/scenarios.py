"""Match the OpenSpec capability specs onto catalogue requirement IDs.

`docs/requirements/openspec/<capability>.md` holds the behavioural specs the
requirement catalogue was derived from. Each file follows the OpenSpec shape:

    ### Requirement: Activación mediante código de un solo uso

    Una cuenta recién creada DEBE quedar en estado pendiente de activación. ...

    #### Scenario: Activación por el titular

    - **GIVEN** una cuenta pendiente con un código de activación vigente
    - **WHEN** el titular canjea el código y define su contraseña
    - **THEN** la cuenta pasa a estado activo

The capability file name maps onto a requirement prefix (the mapping is declared
in the requirements document itself: `CTA = identidad-cuentas`,
`ASI = asistencia-escaneo`, and so on), and each `### Requirement:` heading
matches a catalogue description verbatim. That gives a requirement-level join
with no guessing: every one of the 104 headings resolves to exactly one ID.

Ten prefixes have no capability spec (EST, AUL, HOR, EXP, MAT, MOV, DOC, ARC,
PLA, EMI) and neither do the RNF. Those requirements simply get no scenarios;
nothing is invented for them.
"""

import glob
import os
import re

# Declared in "Reglas de Negocio - SIGA-INEBI" of the requirements document.
CAPABILITY_PREFIXES = {
    "asistencia-escaneo": "ASI",
    "asistencia-jornada": "JOR",
    "asistencia-justificaciones": "JUS",
    "auditoria-bitacora": "BIT",
    "autorizacion-alcance": "ALC",
    "autorizacion-permisos": "PER",
    "ciclo-escolar": "CIC",
    "credencial-estudiantil": "CRE",
    "evaluacion-calificaciones": "CAL",
    "evaluacion-configuracion": "EVC",
    "evaluacion-resultados": "RES",
    "identidad-autenticacion": "AUT",
    "identidad-cuentas": "CTA",
}

_REQUIREMENT_RE = re.compile(r"^###\s+Requirement:\s*(.+?)\s*$", re.M)
_SCENARIO_RE = re.compile(r"^####\s+Scenario:\s*(.+?)\s*$", re.M)


def parse_capability(text):
    """Split one capability spec into requirement blocks.

    Returns a list of {"title", "statement", "scenarios": [{"title", "steps"}]}.
    """
    requirements = []
    matches = list(_REQUIREMENT_RE.finditer(text))

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : end]

        scenario_matches = list(_SCENARIO_RE.finditer(block))
        statement_end = scenario_matches[0].start() if scenario_matches else len(block)
        statement = _collapse(block[:statement_end])

        scenarios = []
        for position, scenario in enumerate(scenario_matches):
            scenario_end = (
                scenario_matches[position + 1].start()
                if position + 1 < len(scenario_matches)
                else len(block)
            )
            scenarios.append(
                {
                    "title": scenario.group(1),
                    "steps": _steps(block[scenario.end() : scenario_end]),
                }
            )

        requirements.append(
            {
                "title": match.group(1),
                "statement": statement,
                "scenarios": scenarios,
            }
        )

    return requirements


def _collapse(text):
    """Join a wrapped paragraph into single-spaced lines, dropping blank runs."""
    paragraphs = [
        " ".join(part.split())
        for part in re.split(r"\n\s*\n", text.strip())
        if part.strip()
    ]
    return "\n\n".join(paragraphs)


def _steps(text):
    """Return the GIVEN/WHEN/THEN/AND bullet lines of a scenario, unwrapped."""
    steps = []
    for raw_line in text.strip().splitlines():
        line = raw_line.strip()
        if line.startswith("-"):
            steps.append(" ".join(line.lstrip("- ").split()))
        elif steps and line:
            # Continuation of the previous bullet.
            steps[-1] += " " + " ".join(line.split())
    return steps


def load(specs_dir, catalogue, normalise):
    """Build {requirement_id: requirement_block} for every catalogue ID matched.

    `catalogue` is the parsed requirements catalogue and `normalise` is the
    accent-insensitive comparison used to join titles to descriptions.
    Returns (matched, unmatched_titles).
    """
    matched = {}
    unmatched = []

    if not os.path.isdir(specs_dir):
        return matched, unmatched

    for path in sorted(glob.glob(os.path.join(specs_dir, "*.md"))):
        capability = os.path.splitext(os.path.basename(path))[0]
        prefix = CAPABILITY_PREFIXES.get(capability)
        if not prefix:
            continue

        with open(path, encoding="utf-8") as handle:
            requirements = parse_capability(handle.read())

        candidates = {
            normalise(entry["description"]): requirement_id
            for requirement_id, entry in catalogue.items()
            if requirement_id.startswith(f"RF-{prefix}-")
        }

        for requirement in requirements:
            requirement_id = candidates.get(normalise(requirement["title"]))
            if requirement_id is None:
                unmatched.append((capability, requirement["title"]))
                continue
            requirement["capability"] = capability
            requirement["source"] = os.path.join(
                "docs", "requirements", "openspec", f"{capability}.md"
            )
            matched[requirement_id] = requirement

    return matched, unmatched
