#!/usr/bin/env sh
# Refresh the body and labels of issues that already exist.
#
#   sh scripts/requirements/update-issues.sh                    # dry-run
#   APPLY=true sh scripts/requirements/update-issues.sh         # writes
#
# Use it when a capability spec changes, when the requirement catalogue changes,
# or when the ticket template itself improves. Reads out/created.tsv for the
# issue numbers, so it only ever touches issues this pipeline created.
#
# It never creates or closes anything: an id absent from created.tsv is skipped.
set -eu

. "$(dirname "$0")/../github/_common.sh"
. "$(dirname "$0")/_preflight.sh"

require_command gh
require_gh_auth
set_repo_context
pin_account
[ "${APPLY:-false}" != "true" ] || require_write_access

OUT_DIR="$(dirname "$0")/out"
EPICS_TSV="${OUT_DIR}/epics.tsv"
TICKETS_TSV="${OUT_DIR}/tickets.tsv"
CREATED_TSV="${OUT_DIR}/created.tsv"

THROTTLE="${THROTTLE:-2}"
TAB=$(printf '\t')

[ -f "${CREATED_TSV}" ] || fail "Missing ${CREATED_TSV}. Nothing has been created yet."
[ -f "${TICKETS_TSV}" ] || fail "Missing ${TICKETS_TSV}. Run render-tickets.py first."

log "Target repository: ${REPO_SLUG}"
log "Dry-run by default. Use APPLY=true to update issues."
log ""

issue_number_for() {
  awk -F'\t' -v key="$1" '$1 == key { print $2; exit }' "${CREATED_TSV}"
}

WORK_BODY="${OUT_DIR}/.body.md"
WANTED_LABELS="${OUT_DIR}/.labels.txt"
trap 'rm -f "${WORK_BODY}" "${WANTED_LABELS}"' EXIT

# Plain render-tickets.py leaves the epic checklists without issue numbers;
# refresh them from created.tsv so the epic bodies stay linked.
require_command python3
python3 "$(dirname "$0")/render-tickets.py" --refresh-epics "${CREATED_TSV}"
log ""

updated=0
skipped=0

log "== Requirements =="
while IFS="${TAB}" read -r id epic title labels body_file; do
  [ -n "${id}" ] || continue

  number=$(issue_number_for "${id}")
  if [ -z "${number}" ]; then
    skipped=$((skipped + 1))
    continue
  fi

  epic_number=$(issue_number_for "epic:${epic}")
  if [ -n "${epic_number}" ]; then
    epic_reference="#${epic_number}"
  else
    epic_reference="epic(${epic}) (pendiente de crear)"
  fi
  sed "s|{{EPIC}}|${epic_reference}|g" "${body_file}" >"${WORK_BODY}"

  if [ "${APPLY:-false}" != "true" ]; then
    log "UPDATE ${id} -> #${number} (${labels})"
    updated=$((updated + 1))
    continue
  fi

  # --add-label is additive; a label the requirement no longer carries has to be
  # removed explicitly, so send the full set both ways.
  gh issue edit "${number}" \
    --repo "${REPO_SLUG}" \
    --title "${title}" \
    --body-file "${WORK_BODY}" >/dev/null

  current=$(gh issue view "${number}" --repo "${REPO_SLUG}" \
    --json labels --jq '[.labels[].name] | sort | join(",")')
  wanted=$(printf '%s' "${labels}" | tr ',' '\n' | sort | paste -sd, -)
  if [ "${current}" != "${wanted}" ]; then
    printf '%s' "${labels}" | tr ',' '\n' >"${WANTED_LABELS}"
    remove=$(printf '%s' "${current}" | tr ',' '\n' |
      grep -Fxv -f "${WANTED_LABELS}" | paste -sd, - || true)
    if [ -n "${remove}" ]; then
      gh issue edit "${number}" --repo "${REPO_SLUG}" \
        --remove-label "${remove}" >/dev/null
    fi
    gh issue edit "${number}" --repo "${REPO_SLUG}" --add-label "${labels}" >/dev/null
    log "UPDATE ${id} -> #${number} (labels: ${current} -> ${wanted})"
  else
    log "UPDATE ${id} -> #${number}"
  fi

  updated=$((updated + 1))
  sleep "${THROTTLE}"
done <"${TICKETS_TSV}"

log ""
log "== Epics =="
while IFS="${TAB}" read -r key title labels body_file; do
  [ -n "${key}" ] || continue
  number=$(issue_number_for "${key}")
  [ -n "${number}" ] || continue

  if [ "${APPLY:-false}" != "true" ]; then
    log "UPDATE ${key} -> #${number}"
    continue
  fi

  gh issue edit "${number}" --repo "${REPO_SLUG}" \
    --title "${title}" --body-file "${body_file}" >/dev/null
  log "UPDATE ${key} -> #${number}"
  sleep "${THROTTLE}"
done <"${EPICS_TSV}"

log ""
if [ "${APPLY:-false}" != "true" ]; then
  log "Dry-run complete. ${updated} issues would be updated, ${skipped} skipped."
  log "Re-run with APPLY=true."
else
  log "Done. ${updated} issues updated, ${skipped} skipped (not in created.tsv)."
fi
