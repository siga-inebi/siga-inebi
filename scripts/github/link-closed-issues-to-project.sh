#!/usr/bin/env sh
# Link closed repository issues that are missing from an existing GitHub Project.
#
#   sh scripts/github/link-closed-issues-to-project.sh
#   APPLY=true sh scripts/github/link-closed-issues-to-project.sh
#
# Override REPO_SLUG, PROJECT_OWNER, or PROJECT_NUMBER when targeting another
# repository or Project. The script only adds items; it does not edit fields.
set -eu

# shellcheck source=_common.sh
. "$(dirname "$0")/_common.sh"

require_command gh
require_command jq
require_gh_auth

REPO_SLUG="${REPO_SLUG:-siga-inebi/siga-inebi}"
PROJECT_OWNER="${PROJECT_OWNER:-siga-inebi}"
PROJECT_NUMBER="${PROJECT_NUMBER:-1}"

WORK_DIR=$(mktemp -d)
trap 'rm -rf "${WORK_DIR}"' EXIT

CLOSED_JSON="${WORK_DIR}/closed.json"
PROJECT_JSON="${WORK_DIR}/project.json"
MISSING_TSV="${WORK_DIR}/missing.tsv"
TAB=$(printf '\t')

case "${REPO_SLUG}" in
  */*)
    repo_owner=${REPO_SLUG%%/*}
    repo_name=${REPO_SLUG#*/}
    ;;
  *)
    fail "REPO_SLUG must use the owner/name format: ${REPO_SLUG}"
    ;;
esac

[ -n "${repo_owner}" ] && [ -n "${repo_name}" ] ||
  fail "REPO_SLUG must use the owner/name format: ${REPO_SLUG}"
case "${repo_name}" in
  */*) fail "REPO_SLUG must use the owner/name format: ${REPO_SLUG}" ;;
esac

gh issue list \
  --repo "${REPO_SLUG}" \
  --state closed \
  --limit 1000 \
  --json number,url >"${CLOSED_JSON}"

gh project item-list "${PROJECT_NUMBER}" \
  --owner "${PROJECT_OWNER}" \
  --limit 1000 \
  --format json >"${PROJECT_JSON}"

# GraphQL variables must remain literal for gh to bind them through -F.
# shellcheck disable=SC2016
closed_issue_total=$(gh api graphql \
  -f 'query=query($owner:String!,$name:String!){repository(owner:$owner,name:$name){issues(states:CLOSED){totalCount}}}' \
  -F "owner=${repo_owner}" \
  -F "name=${repo_name}" \
  --jq '.data.repository.issues.totalCount')

returned_issue_count=$(jq -er 'length' "${CLOSED_JSON}")
[ "${returned_issue_count}" -eq "${closed_issue_total}" ] ||
  fail "Closed issue list was truncated: received ${returned_issue_count} of ${closed_issue_total} issues"

returned_item_count=$(jq -er '.items | length' "${PROJECT_JSON}")
total_item_count=$(jq -er '.totalCount' "${PROJECT_JSON}")
[ "${returned_item_count}" -eq "${total_item_count}" ] ||
  fail "Project item list was truncated: received ${returned_item_count} of ${total_item_count} items"

jq -r --slurpfile project "${PROJECT_JSON}" '
  ($project[0].items | map(.content.url)) as $present
  | .[]
  | select(.url as $url | ($present | index($url)) == null)
  | [.number, .url]
  | @tsv
' "${CLOSED_JSON}" >"${MISSING_TSV}"

missing=$(wc -l <"${MISSING_TSV}" | tr -d ' ')

log "Repository: ${REPO_SLUG}"
log "Project: ${PROJECT_OWNER}/${PROJECT_NUMBER}"

if [ "${missing}" -eq 0 ]; then
  log "No closed issues are missing from the Project."
  exit 0
fi

if [ "${APPLY:-false}" != "true" ]; then
  while IFS="${TAB}" read -r number url; do
    log "LINK #${number} ${url}"
  done <"${MISSING_TSV}"
  log "Dry-run complete. ${missing} closed issues would be linked."
  log "Re-run with APPLY=true using an account with Project write access."
  exit 0
fi

linked=0
while IFS="${TAB}" read -r number url; do
  gh project item-add "${PROJECT_NUMBER}" \
    --owner "${PROJECT_OWNER}" \
    --url "${url}" >/dev/null
  linked=$((linked + 1))
  log "LINKED #${number}"
done <"${MISSING_TSV}"

log "Complete. ${linked} closed issues linked to the Project."
