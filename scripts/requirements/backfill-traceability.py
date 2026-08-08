#!/usr/bin/env python3
"""Write the created issue numbers back into the requirements documentation.

    python3 scripts/requirements/backfill-traceability.py            # dry-run
    APPLY=true python3 scripts/requirements/backfill-traceability.py # writes

Fills the `Issue relacionado` column of docs/requirements/requirements-catalogue.md
and the `Issue` column of docs/requirements/traceability-matrix.md from
out/created.tsv.

`docs/requirements/change-control.md` requires that every implemented or tracked
requirement carries its issue reference. Idempotent: a second run makes no
further change.
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CATALOGUE = os.path.join(REPO_ROOT, "docs", "requirements", "requirements-catalogue.md")
MATRIX = os.path.join(REPO_ROOT, "docs", "requirements", "traceability-matrix.md")
DEFAULT_CREATED = os.path.join(HERE, "out", "created.tsv")

ID_RE = r"(?:RF|RNF)-[A-Z]{3}-\d{3}"
# A cell we are allowed to overwrite: still a placeholder, or an issue reference
# we wrote on an earlier run.
REPLACEABLE = re.compile(r"^(?:TBD|#\d+)$")


def load_created(path):
    """Read out/created.tsv into {requirement_id: issue_number}, skipping epics."""
    created = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 2 or not fields[0] or fields[0].startswith("epic:"):
                continue
            if re.fullmatch(ID_RE, fields[0]):
                created[fields[0]] = fields[1]
    return created


def patch_table(text, created, id_column, issue_column):
    """Rewrite `issue_column` of every markdown row whose `id_column` is a known ID.

    Column indexes are zero-based over the cells between the outer pipes.
    Returns (new_text, changed_count, skipped_ids).
    """
    output = []
    changed = 0
    skipped = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            output.append(line)
            continue

        cells = stripped[1:-1].split("|")
        if len(cells) <= max(id_column, issue_column):
            output.append(line)
            continue

        requirement_id = cells[id_column].strip()
        if not re.fullmatch(ID_RE, requirement_id):
            output.append(line)
            continue

        if requirement_id not in created:
            skipped.append(requirement_id)
            output.append(line)
            continue

        current = cells[issue_column].strip()
        if not REPLACEABLE.match(current):
            # Somebody filled this in by hand; leave it alone.
            output.append(line)
            continue

        replacement = f"#{created[requirement_id]}"
        if current == replacement:
            output.append(line)
            continue

        cells[issue_column] = f" {replacement} "
        output.append("|" + "|".join(cells) + "|")
        changed += 1

    trailing_newline = "\n" if text.endswith("\n") else ""
    return "\n".join(output) + trailing_newline, changed, skipped


def process(path, created, id_column, issue_column, apply_changes):
    with open(path, encoding="utf-8") as handle:
        original = handle.read()

    patched, changed, skipped = patch_table(original, created, id_column, issue_column)
    relative = os.path.relpath(path, REPO_ROOT)

    if changed and apply_changes:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(patched)
        print(f"UPDATED {relative}: {changed} rows")
    elif changed:
        print(f"WOULD UPDATE {relative}: {changed} rows")
    else:
        print(f"UNCHANGED {relative}")

    if skipped:
        unique = sorted(set(skipped))
        print(f"  {len(unique)} rows had no issue in created.tsv: {', '.join(unique)}")

    return changed


def main():
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("--created", default=DEFAULT_CREATED)
    args = argument_parser.parse_args()

    if not os.path.exists(args.created):
        sys.exit(
            f"ERROR: {args.created} not found. "
            "Run create-issues.sh with APPLY=true first."
        )

    created = load_created(args.created)
    if not created:
        sys.exit(f"ERROR: no requirement issues recorded in {args.created}")
    print(f"Read {len(created)} created issues from {args.created}")

    apply_changes = os.environ.get("APPLY", "false") == "true"
    if not apply_changes:
        print("Dry-run by default. Use APPLY=true to write the files.")
    print()

    # Catalogue: | ID | Descripcion | Prioridad | Dominio | Estado | Issue relacionado | ...
    total = process(CATALOGUE, created, id_column=0, issue_column=5, apply_changes=apply_changes)
    # Matrix: | Requirement | Issue | Design | Code | Test | Pull Request | Status | Notes |
    total += process(MATRIX, created, id_column=0, issue_column=1, apply_changes=apply_changes)

    print()
    if apply_changes:
        print(f"Done. {total} rows now reference a real issue.")
    else:
        print(f"Dry-run complete. {total} rows would change.")


if __name__ == "__main__":
    main()
