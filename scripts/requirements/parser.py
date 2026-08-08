"""Pure parsing helpers for the requirement traceability cards.

The source is the text layer of "INEBI Fase 2.pdf" as produced by
`pdftotext -layout`. Pages 80-188 hold one two-column card per requirement:

    Código del requerimiento   RF-ASI-001
    Nombre                     Captura mediada por operador
    ...
    Criterio de aceptación     El sistema debe determinar la ventana operativa
                               diaria habilitada para la recepcion de eventos.

Labels always start at column 0 and values wrap onto indented continuation
lines. Cards routinely straddle page breaks, so form feeds are discarded and
the document is parsed as a single stream.

Nothing here touches the filesystem or the network, so it is directly testable.
"""

import re
import unicodedata

# The ten card labels, longest first so that alternation cannot match a prefix
# of a longer label.
CARD_LABELS = (
    "Código del requerimiento",
    "Criterio de aceptación",
    "Usuario relacionado",
    "Historia de usuario",
    "Regla de negocio",
    "Prioridad",
    "Nombre",
    "Fuente",
    "Módulo",
    "Estado",
)

FIELD_KEYS = {
    "Código del requerimiento": "id",
    "Nombre": "name",
    "Fuente": "source",
    "Usuario relacionado": "actor",
    "Historia de usuario": "user_story",
    "Regla de negocio": "business_rule",
    "Prioridad": "priority",
    "Criterio de aceptación": "acceptance_criteria",
    "Módulo": "module",
    "Estado": "status",
}

_LABEL_RE = re.compile(r"^(%s)(?:\s+(.*))?$" % "|".join(re.escape(l) for l in CARD_LABELS))
_ID_RE = re.compile(r"^(RF|RNF)-([A-Z]{3})-(\d{3})$")

# Boilerplate that repeats on every page of the matrix and must never be read
# as a continuation line.
_NOISE_RE = re.compile(r"^\s*Campo\s+Detalle\s*$")


def normalise(value):
    """Lowercase, strip accents and punctuation. Used only to compare names."""
    decomposed = unicodedata.normalize("NFKD", value.lower())
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", " ", without_accents).strip()


def parse_cards(text):
    """Parse every requirement card out of the pdftotext output.

    Returns a list of dicts keyed by FIELD_KEYS values, in document order.
    Cards whose code is not a well-formed requirement ID are skipped, which
    discards the stray table fragments outside the matrix section.
    """
    cards = []
    current = None
    last_key = None

    for raw_line in text.replace("\f", "\n").splitlines():
        if _NOISE_RE.match(raw_line):
            last_key = None
            continue

        match = _LABEL_RE.match(raw_line)
        if match:
            label, value = match.group(1), (match.group(2) or "").strip()
            key = FIELD_KEYS[label]
            if key == "id":
                current = {"id": value}
                cards.append(current)
            elif current is None:
                continue
            else:
                current[key] = value
            last_key = key
            continue

        # Continuation: indented, non-empty, and we are inside a field.
        if current is not None and last_key and raw_line.startswith(" ") and raw_line.strip():
            current[last_key] = (current.get(last_key, "") + " " + raw_line.strip()).strip()

    return [card for card in cards if _ID_RE.match(card.get("id", ""))]


def split_id(requirement_id):
    """Split RF-ASI-001 into ("RF", "ASI", "001")."""
    match = _ID_RE.match(requirement_id)
    if not match:
        raise ValueError(f"Malformed requirement id: {requirement_id!r}")
    return match.group(1), match.group(2), match.group(3)


def choose_canonical(cards, catalogue_name):
    """Pick the authoritative card when several share one requirement ID.

    The PDF reuses six IDs for entirely different requirements (an earlier draft
    left behind next to the final one). The catalogue is the authority on what
    an ID means, so prefer the card whose name matches it; otherwise fall back
    to the last occurrence, which is the one the final tables agree with.
    """
    if len(cards) == 1:
        return cards[0], True

    target = normalise(catalogue_name or "")
    for card in cards:
        if normalise(card.get("name", "")) == target:
            return card, True
    return cards[-1], False


def parse_catalogue(markdown):
    """Read docs/requirements/requirements-catalogue.md.

    Returns {id: {"description", "priority", "domain"}} for every RF and RNF row.
    """
    entries = {}
    row_re = re.compile(
        r"^\|\s*((?:RF|RNF)-[A-Z]{3}-\d{3})\s*\|"  # id
        r"\s*([^|]*?)\s*\|"  # description
        r"\s*([^|]*?)\s*\|"  # priority
        r"\s*([^|]*?)\s*\|"  # domain
    )
    for line in markdown.splitlines():
        match = row_re.match(line)
        if match:
            entries[match.group(1)] = {
                "description": match.group(2),
                "priority": match.group(3),
                "domain": match.group(4),
            }
    return entries
