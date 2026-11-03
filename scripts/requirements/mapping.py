"""Mapping tables that turn a requirement record into GitHub issue metadata.

Every mapping decision lives here so that a reviewer can audit the whole
translation from requirement to ticket in one file.

Sources:
- Epics come from "Lista priorizada de funcionalidades" (INEBI Fase 2.pdf, p. 74-77).
- Labels come from the taxonomy already provisioned by
  scripts/github/configure-labels.sh.
- Domains come from the `Dominio` column of docs/requirements/requirements-catalogue.md.
"""

# --- Epics ---------------------------------------------------------------
# Six functional epics taken verbatim from the prioritised feature list, plus a
# seventh that collects every non-functional requirement.

EPICS = [
    {
        "key": "seguridad",
        "title": "Seguridad, cuentas y autenticacion",
        "priority": "Alta",
        "prefixes": ["AUT", "CTA", "PER", "BIT", "ALC"],
        "summary": (
            "Gestion de cuentas de usuario, control de inicio de sesion, asignacion "
            "de roles y permisos atomicos, control de alcances por usuario y "
            "bitacoras de operaciones inmutables."
        ),
    },
    {
        "key": "estructura",
        "title": "Estructura institucional y ciclo escolar",
        "priority": "Alta",
        "prefixes": ["CIC", "EST", "AUL", "HOR"],
        "summary": (
            "Configuracion de ciclos escolares, grados, secciones, cupos, asignacion "
            "de docentes a subareas, gestion de aulas fisicas y la rejilla de "
            "horarios institucionales con deteccion de cruces."
        ),
    },
    {
        "key": "expedientes",
        "title": "Expedientes, documentos y matricula",
        "priority": "Alta",
        "prefixes": ["EXP", "MAT", "MOV", "DOC", "ARC", "CRE"],
        "summary": (
            "Registro completo del estudiante y sus vinculos, digitalizacion y "
            "control de documentos de expediente, emision de credenciales con codigo "
            "QR, procesos de inscripcion, reinscripcion y movimientos."
        ),
    },
    {
        "key": "asistencia",
        "title": "Control de asistencia y jornadas",
        "priority": "Alta",
        "prefixes": ["ASI", "JOR", "JUS"],
        "summary": (
            "Puntos de control por escaneo de codigo QR, derivacion del estado de "
            "asistencia diario, calculo de porcentajes del ciclo, alertas y el "
            "submodulo de justificaciones de inasistencia."
        ),
    },
    {
        "key": "evaluacion",
        "title": "Gestion academica y calificaciones",
        "priority": "Alta",
        "prefixes": ["EVC", "CAL", "RES"],
        "summary": (
            "Configuracion de unidades del ciclo escolar, ventanas de captura de "
            "notas, escalas y validaciones de calificaciones, calculo de notas "
            "finales, recuperaciones y criterios de promocion."
        ),
    },
    {
        "key": "emision",
        "title": "Plantillas, emision y reporteria",
        "priority": "Media",
        "prefixes": ["PLA", "EMI"],
        "summary": (
            "Catalogo de plantillas institucionales con campos controlados, emision "
            "individual o por lote de documentos oficiales con codigos de "
            "verificacion y folios correlativos."
        ),
    },
    {
        "key": "plataforma",
        "title": "Plataforma, calidad y cumplimiento",
        "priority": "Alta",
        "prefixes": [],  # every RNF lands here
        "summary": (
            "Requerimientos no funcionales: auditoria, capacidad, compatibilidad, "
            "consistencia, disponibilidad, cumplimiento legal, localizacion, "
            "mantenibilidad, operacion, privacidad, rendimiento, respaldo, seguridad "
            "y usabilidad."
        ),
    },
]

RNF_EPIC_KEY = "plataforma"

_EPIC_BY_PREFIX = {
    prefix: epic["key"] for epic in EPICS for prefix in epic["prefixes"]
}


# --- Conventional-commit scopes ------------------------------------------
# Keyed by (kind, prefix) because RF-RES (resultados) and RNF-RES (respaldo)
# are different concerns that share a prefix.

SCOPES = {
    ("RF", "ALC"): "alcances",
    ("RF", "ARC"): "archivos",
    ("RF", "ASI"): "asistencia",
    ("RF", "AUL"): "aulas",
    ("RF", "AUT"): "auth",
    ("RF", "BIT"): "bitacora",
    ("RF", "CAL"): "calificaciones",
    ("RF", "CIC"): "ciclo",
    ("RF", "CRE"): "credencial",
    ("RF", "CTA"): "cuentas",
    ("RF", "DOC"): "documentos",
    ("RF", "EMI"): "emision",
    ("RF", "EST"): "estructura",
    ("RF", "EVC"): "evaluacion",
    ("RF", "EXP"): "expediente",
    ("RF", "HOR"): "horarios",
    ("RF", "JOR"): "jornada",
    ("RF", "JUS"): "justificaciones",
    ("RF", "MAT"): "matricula",
    ("RF", "MOV"): "movimientos",
    ("RF", "PER"): "permisos",
    ("RF", "PLA"): "plantillas",
    ("RF", "RES"): "resultados",
    ("RNF", "AUD"): "auditoria",
    ("RNF", "CAP"): "capacidad",
    ("RNF", "COM"): "compatibilidad",
    ("RNF", "CON"): "consistencia",
    ("RNF", "DIS"): "disponibilidad",
    ("RNF", "LEG"): "legal",
    ("RNF", "LOC"): "localizacion",
    ("RNF", "MAN"): "mantenibilidad",
    ("RNF", "OPE"): "operacion",
    ("RNF", "PRI"): "privacidad",
    ("RNF", "REN"): "rendimiento",
    ("RNF", "RES"): "respaldo",
    ("RNF", "SEG"): "seguridad",
    ("RNF", "USA"): "usabilidad",
}


# --- Labels --------------------------------------------------------------
# The PDF cards use MoSCoW in Spanish; a handful use Alta/Media/Baja instead.
# Both vocabularies map onto the same priority labels.

PRIORITY_LABELS = {
    "Debe": "priority:high",
    "Alta": "priority:high",
    "Deberia": "priority:medium",
    "Media": "priority:medium",
    "Podria": "priority:low",
    "Baja": "priority:low",
}

AREA_LABELS = {
    "identity-access": "area:security",
    "security-compliance": "area:security",
    "audit-compliance": "area:security",
    "frontend-platform": "area:frontend",
    "platform": "area:devops",
}

DEFAULT_AREA_LABEL = "area:backend"

# Some non-functional prefixes are security concerns whatever domain the
# catalogue filed them under: RNF-SEG-004 sits in `document-generation` but it is
# still a security requirement. The prefix wins so that every security item is
# findable by one label.
SECURITY_PREFIXES = {"SEG", "PRI", "LEG"}

TYPE_LABELS = {"RF": "type:feature", "RNF": "type:chore"}

# Applied when neither the requirements document nor a capability spec says what
# the requirement must do: the ticket cannot be worked until somebody writes it.
BLOCKED_LABEL = "status:blocked"


def _strip_accents(value):
    import unicodedata

    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def epic_key_for(kind, prefix):
    """Return the epic key that owns a requirement prefix."""
    if kind == "RNF":
        return RNF_EPIC_KEY
    try:
        return _EPIC_BY_PREFIX[prefix]
    except KeyError:
        raise KeyError(f"No epic mapped for prefix {prefix!r} (kind {kind!r})")


def scope_for(kind, prefix):
    """Return the conventional-commit scope for a requirement prefix."""
    try:
        return SCOPES[(kind, prefix)]
    except KeyError:
        raise KeyError(f"No scope mapped for {kind}-{prefix}")


def priority_label_for(priority):
    """Return the priority label for a MoSCoW or Alta/Media/Baja value."""
    try:
        return PRIORITY_LABELS[_strip_accents(priority.strip())]
    except KeyError:
        raise KeyError(f"Unknown priority value {priority!r}")


def area_label_for(domain, prefix=None):
    """Return the area label for a catalogue domain.

    A security-bearing prefix overrides the domain.
    """
    if prefix in SECURITY_PREFIXES:
        return "area:security"
    return AREA_LABELS.get(domain, DEFAULT_AREA_LABEL)


def labels_for(record):
    """Return the ordered label list for a requirement record."""
    labels = [
        TYPE_LABELS[record["kind"]],
        area_label_for(record["domain"], record.get("prefix")),
        priority_label_for(record["priority"]),
    ]
    # A capability spec is a valid statement of expected behaviour, so a
    # requirement with a spec is workable even when the PDF has no card for it.
    if not record.get("acceptance_criteria") and not record.get("spec"):
        labels.append(BLOCKED_LABEL)
    return labels


def title_for(record):
    """Return the conventional-commit issue title for a requirement record."""
    prefix = "feat" if record["kind"] == "RF" else "chore"
    scope = scope_for(record["kind"], record["prefix"])
    return f"{prefix}({scope}): {record['id']} {record['name']}"


def epic_title_for(epic):
    """Return the issue title for an epic."""
    return f"epic({epic['key']}): {epic['title']}"


def epic_labels_for(epic):
    """Return the label list for an epic.

    An epic spans several areas, so it carries no `area:` label; the children do.
    """
    type_label = "type:chore" if epic["key"] == RNF_EPIC_KEY else "type:feature"
    return [type_label, priority_label_for(epic["priority"])]
