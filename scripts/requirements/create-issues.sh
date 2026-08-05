#!/usr/bin/env sh
# Create one GitHub issue per requirement, grouped under seven epic issues.
#
#   sh scripts/requirements/create-issues.sh                      # dry-run
#   APPLY=true sh scripts/requirements/create-issues.sh           # writes
#
# Target another repository (the sandbox rehearsal) with:
#
#   GITHUB_ORG=daniel-baf GITHUB_REPO=inebi-tickets-sandbox \
#     APPLY=true sh scripts/requirements/create-issues.sh
#
# Every successful creation is appended to out/created.tsv immediately, and
# anything already listed there is skipped. An interrupted run resumes without
# creating duplicates.
set -eu

. "$(dirname "$0")/../github/_common.sh"
. "$(dirname "$0")/_preflight.sh"

require_command gh
require_command python3
require_gh_auth
set_repo_context
pin_account
[ "${APPLY:-false}" != "true" ] || require_write_access

OUT_DIR="$(dirname "$0")/out"
EPICS_TSV="${OUT_DIR}/epics.tsv"
TICKETS_TSV="${OUT_DIR}/tickets.tsv"
CREATED_TSV="${OUT_DIR}/created.tsv"

# Seconds between write requests. GitHub's secondary rate limit rejects bursts of
# content-creating calls; it asks for at least one second between them.
THROTTLE="${THROTTLE:-2}"

TAB=$(printf '\t')

[ -f "${EPICS_TSV}" ] || fail "Missing ${EPICS_TSV}. Run render-tickets.py first."
[ -f "${TICKETS_TSV}" ] || fail "Missing ${TICKETS_TSV}. Run render-tickets.py first."

log "Target repository: ${REPO_SLUG}"
log "Dry-run by default. Use APPLY=true to create issues."
log ""

touch "${CREATED_TSV}"

already_created() {
  cut -f1 "${CREATED_TSV}" | grep -Fxq "$1"
}

record_created() {
  # key, issue number, url
  printf '%s\t%s\t%s\n' "$1" "$2" "$3" >>"${CREATED_TSV}"
}

issue_number_for() {
  awk -F'\t' -v key="$1" '$1 == key { print $2; exit }' "${CREATED_TSV}"
}

# Extract the issue number from the URL gh prints on success.
number_from_url() {
  printf '%s' "$1" | sed -E 's#.*/issues/([0-9]+).*#\1#'
}

create_issue() {
  key="$1"
  title="$2"
  labels="$3"
  body_file="$4"

  if already_created "${key}"; then
    log "SKIP   ${key} (already in created.tsv as #$(issue_number_for "${key}"))"
    return 0
  fi

  if [ "${APPLY:-false}" != "true" ]; then
    log "CREATE ${key}"
    log "       title:  ${title}"
    log "       labels: ${labels}"
    log "       body:   ${body_file}"
    return 0
  fi

  url=$(gh issue create \
    --repo "${REPO_SLUG}" \
    --title "${title}" \
    --label "${labels}" \
    --body-file "${body_file}")
  number=$(number_from_url "${url}")
  [ -n "${number}" ] || fail "Could not read an issue number out of: ${url}"
  record_created "${key}" "${number}" "${url}"
  log "CREATE ${key} -> #${number}"
  sleep "${THROTTLE}"
}

# --- Epics first: children reference their number ------------------------
log "== Epics =="
while IFS="${TAB}" read -r key title labels body_file; do
  [ -n "${key}" ] || continue
  create_issue "${key}" "${title}" "${labels}" "${body_file}"
done <"${EPICS_TSV}"

log ""
log "== Requirements =="

WORK_BODY="${OUT_DIR}/.body.md"
trap 'rm -f "${WORK_BODY}"' EXIT

while IFS="${TAB}" read -r id epic title labels body_file; do
  [ -n "${id}" ] || continue

  epic_number=$(issue_number_for "epic:${epic}")
  if [ -n "${epic_number}" ]; then
    epic_reference="#${epic_number}"
  else
    epic_reference="epic(${epic}) (pendiente de crear)"
  fi

  # Substitute the epic placeholder without touching the rendered file.
  sed "s|{{EPIC}}|${epic_reference}|g" "${body_file}" >"${WORK_BODY}"
  create_issue "${id}" "${title}" "${labels}" "${WORK_BODY}"
done <"${TICKETS_TSV}"

log ""
if [ "${APPLY:-false}" != "true" ]; then
  planned=$(( $(wc -l <"${EPICS_TSV}") + $(wc -l <"${TICKETS_TSV}") ))
  log "Dry-run complete. ${planned} issues would be created in ${REPO_SLUG}."
  log "Re-run with APPLY=true to create them."
  exit 0
fi

# --- Backfill each epic body with a task list of its children -----------
log "== Refreshing epic bodies with their child issue numbers =="
python3 "$(dirname "$0")/render-tickets.py" --refresh-epics "${CREATED_TSV}"

while IFS="${TAB}" read -r key title labels body_file; do
  [ -n "${key}" ] || continue
  number=$(issue_number_for "${key}")
  [ -n "${number}" ] || continue
  gh issue edit "${number}" --repo "${REPO_SLUG}" --body-file "${body_file}" >/dev/null
  log "UPDATE ${key} -> #${number}"
  sleep "${THROTTLE}"
done <"${EPICS_TSV}"

log ""
log "Done. Created issues are recorded in ${CREATED_TSV}."
log "Next: python3 scripts/requirements/backfill-traceability.py"
