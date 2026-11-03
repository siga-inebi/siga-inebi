#!/usr/bin/env python3
"""Extract the requirement traceability cards from the requirements PDF.

    python3 scripts/requirements/extract-requirements.py

Writes `docs/requirements/requirements.json` with one record per catalogue
requirement and `out/extraction-report.md` with everything a human has to decide.

The JSON is versioned on purpose: the PDF is a 21 MB binary that git cannot diff,
so it stays out of the repository and this file is what the rest of the pipeline
reads. A fresh clone can render and create tickets without the PDF; only
re-extraction needs it.

The requirements catalogue is the authority: it owns the set of valid IDs, the
MoSCoW priority and the domain. The PDF cards contribute what only they carry -
the acceptance criterion, the actor, the user story, the business rule and the
module. The run aborts if the PDF describes an ID the catalogue does not know,
because that means the two documents have drifted apart.
"""

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mapping  # noqa: E402
import parser as cards_parser  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_PDF = os.path.join(REPO_ROOT, "INEBI Fase 2.pdf")
CATALOGUE = os.path.join(REPO_ROOT, "docs", "requirements", "requirements-catalogue.md")
DEFAULT_OUT = os.path.join(HERE, "out")
# Versioned: this is what render-tickets.py reads, so the pipeline works from a
# clean clone that does not carry the PDF.
DEFAULT_REQUIREMENTS = os.path.join(
    REPO_ROOT, "docs", "requirements", "requirements.json"
)


def pdf_to_text(pdf_path):
    """Return the text layer of the PDF, preserving the two-column layout."""
    try:
        completed = subprocess.run(
            ["pdftotext", "-layout", pdf_path, "-"],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        sys.exit("ERROR: pdftotext not found. Install poppler-utils.")
    except subprocess.CalledProcessError as error:
        sys.exit(f"ERROR: pdftotext failed: {error.stderr.decode(errors='replace')}")
    return completed.stdout.decode("utf-8", errors="replace")


def build_records(cards, catalogue):
    """Join cards onto catalogue rows, resolving duplicate IDs.

    Returns (records, collisions, unmatched_collisions, without_card, orphans).
    """
    by_id = {}
    for card in cards:
        by_id.setdefault(card["id"], []).append(card)

    unknown = sorted(set(by_id) - set(catalogue))
    if unknown:
        sys.exit(
            "ERROR: the PDF describes requirement IDs absent from the catalogue: "
            + ", ".join(unknown)
        )

    records = []
    collisions = []
    unmatched_collisions = []
    without_card = []
    orphans = []

    for requirement_id in sorted(catalogue):
        entry = catalogue[requirement_id]
        kind, prefix, _ = cards_parser.split_id(requirement_id)
        candidates = by_id.get(requirement_id, [])

        if candidates:
            card, matched = cards_parser.choose_canonical(
                candidates, entry["description"]
            )
            if len(candidates) > 1:
                collisions.append(requirement_id)
                if not matched:
                    unmatched_collisions.append(requirement_id)
                for discarded in candidates:
                    if discarded is not card:
                        orphans.append(
                            {
                                "shared_id": requirement_id,
                                "name": discarded.get("name", ""),
                                "source": discarded.get("source", ""),
                                "priority": discarded.get("priority", ""),
                                "module": discarded.get("module", ""),
                                "acceptance_criteria": discarded.get(
                                    "acceptance_criteria", ""
                                ),
                            }
                        )
        else:
            card = {}
            without_card.append(requirement_id)

        records.append(
            {
                "id": requirement_id,
                "kind": kind,
                "prefix": prefix,
                # The card spells names with accents; the catalogue does not.
                "name": card.get("name") or entry["description"],
                "catalogue_description": entry["description"],
                # Priority and domain always come from the catalogue: two cards
                # have a mangled priority line.
                "priority": entry["priority"],
                "domain": entry["domain"],
                "epic": mapping.epic_key_for(kind, prefix),
                "actor": card.get("actor", ""),
                "user_story": card.get("user_story", ""),
                "business_rule": card.get("business_rule", ""),
                "acceptance_criteria": card.get("acceptance_criteria", ""),
                "module": card.get("module", ""),
                "source": card.get("source", ""),
                "has_card": bool(candidates),
            }
        )

    return records, collisions, unmatched_collisions, without_card, orphans


def write_report(path, records, collisions, unmatched, without_card, orphans):
    lines = [
        "# Extraction report",
        "",
        "Generated by `scripts/requirements/extract-requirements.py`.",
        "",
        f"- Requirements in the catalogue: **{len(records)}**",
        f"- With an acceptance criterion from the PDF: "
        f"**{sum(1 for r in records if r['acceptance_criteria'])}**",
        f"- Without any card in the PDF: **{len(without_card)}**",
        f"- Requirement IDs used twice by the PDF: **{len(collisions)}**",
        "",
        "## Requirements with no card in the PDF",
        "",
        "These have no acceptance criterion anywhere in the source document. Their",
        "tickets are labelled `status:blocked`: somebody has to write the criterion",
        "before the work can start.",
        "",
    ]
    if without_card:
        lines += ["| ID | Descripcion del catalogo |", "| --- | --- |"]
        catalogue_by_id = {r["id"]: r for r in records}
        lines += [
            f"| `{rid}` | {catalogue_by_id[rid]['catalogue_description']} |"
            for rid in without_card
        ]
    else:
        lines.append("None.")

    lines += [
        "",
        "## Requirement IDs the PDF assigns to two different requirements",
        "",
        "The catalogue decides what an ID means, so the card whose name matches the",
        "catalogue wins. The discarded cards are listed below; they are **not**",
        "turned into tickets.",
        "",
    ]
    if collisions:
        lines += [f"- `{rid}`" for rid in collisions]
    else:
        lines.append("None.")

    if unmatched:
        lines += [
            "",
            "### Collisions where no card matched the catalogue name",
            "",
            "Resolved by taking the last card in document order. Worth a human look.",
            "",
        ]
        lines += [f"- `{rid}`" for rid in unmatched]

    lines += [
        "",
        "## Discarded cards (content with no valid ID)",
        "",
        "Real requirement text that the PDF filed under an ID already taken by",
        "another requirement. Each one is either an earlier draft of a requirement",
        "that does have an ID, or content missing from the catalogue entirely.",
        "",
    ]
    for orphan in orphans:
        lines += [
            f"### {orphan['name']}",
            "",
            f"- Shared the ID `{orphan['shared_id']}`",
            f"- Fuente: {orphan['source'] or 'n/d'}",
            f"- Prioridad: {orphan['priority'] or 'n/d'}",
            f"- Modulo: {orphan['module'] or 'n/d'}",
            "",
            f"> {orphan['acceptance_criteria'] or 'Sin criterio de aceptacion.'}",
            "",
        ]
    if not orphans:
        lines.append("None.")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("--pdf", default=DEFAULT_PDF)
    argument_parser.add_argument("--catalogue", default=CATALOGUE)
    argument_parser.add_argument("--out", default=DEFAULT_OUT)
    argument_parser.add_argument("--requirements", default=DEFAULT_REQUIREMENTS)
    args = argument_parser.parse_args()

    if not os.path.exists(args.pdf):
        sys.exit(f"ERROR: PDF not found: {args.pdf}")

    with open(args.catalogue, encoding="utf-8") as handle:
        catalogue = cards_parser.parse_catalogue(handle.read())
    if not catalogue:
        sys.exit(f"ERROR: no requirement rows found in {args.catalogue}")

    cards = cards_parser.parse_cards(pdf_to_text(args.pdf))
    print(f"Parsed {len(cards)} cards from the PDF.")
    print(f"Read {len(catalogue)} requirements from the catalogue.")

    records, collisions, unmatched, without_card, orphans = build_records(
        cards, catalogue
    )

    # Fail fast on a mapping table that does not cover the data.
    for record in records:
        mapping.labels_for(record)
        mapping.title_for(record)

    os.makedirs(args.out, exist_ok=True)
    requirements_path = args.requirements
    os.makedirs(os.path.dirname(requirements_path), exist_ok=True)
    with open(requirements_path, "w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    report_path = os.path.join(args.out, "extraction-report.md")
    write_report(report_path, records, collisions, unmatched, without_card, orphans)

    with_criteria = sum(1 for r in records if r["acceptance_criteria"])
    print(f"Wrote {len(records)} records to {requirements_path}")
    print(f"  with acceptance criterion: {with_criteria}")
    print(f"  without any card in the PDF: {len(without_card)}")
    print(f"  colliding IDs resolved: {len(collisions)}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
