#!/usr/bin/env sh
set -eu

. "$(dirname "$0")/_common.sh"

require_command gh
require_command python3
require_gh_auth
set_repo_context

STAMP=$(date +"%Y%m%d-%H%M%S")
OUTPUT_DIR="${OUTPUT_DIR:-.tmp/github-export-${STAMP}}"
mkdir -p "${OUTPUT_DIR}"

log "Exporting GitHub settings for ${REPO_SLUG} -> ${OUTPUT_DIR}"

gh_api "repos/${REPO_SLUG}" | json_pp > "${OUTPUT_DIR}/repo.json"
gh_api "repos/${REPO_SLUG}/branches" | json_pp > "${OUTPUT_DIR}/branches.json"
gh_api "repos/${REPO_SLUG}/actions/permissions" | json_pp > "${OUTPUT_DIR}/actions-permissions.json"
gh_api "repos/${REPO_SLUG}/actions/permissions/workflow" | json_pp > "${OUTPUT_DIR}/workflow-permissions.json"
gh_api "repos/${REPO_SLUG}/actions/secrets" | json_pp > "${OUTPUT_DIR}/secrets.json"
gh_api "repos/${REPO_SLUG}/hooks" | json_pp > "${OUTPUT_DIR}/hooks.json"
gh_api "repos/${REPO_SLUG}/labels?per_page=100" | json_pp > "${OUTPUT_DIR}/labels.json"
gh_api "orgs/${GITHUB_ORG}/teams?per_page=100" | json_pp > "${OUTPUT_DIR}/teams.json"
gh_api "repos/${REPO_SLUG}/collaborators?per_page=100&affiliation=all" | json_pp > "${OUTPUT_DIR}/collaborators.json"

if gh_api "repos/${REPO_SLUG}/rulesets" >/tmp/github-rulesets.$$ 2>/tmp/github-rulesets.err.$$; then
  cat /tmp/github-rulesets.$$ | json_pp > "${OUTPUT_DIR}/rulesets.json"
else
  cp /tmp/github-rulesets.err.$$ "${OUTPUT_DIR}/rulesets-error.txt"
fi

if gh_api "repos/${REPO_SLUG}/branches/main/protection" >/tmp/github-main-protection.$$ 2>/tmp/github-main-protection.err.$$; then
  cat /tmp/github-main-protection.$$ | json_pp > "${OUTPUT_DIR}/main-protection.json"
else
  cp /tmp/github-main-protection.err.$$ "${OUTPUT_DIR}/main-protection-error.txt"
fi

if gh_api "repos/${REPO_SLUG}/branches/develop/protection" >/tmp/github-develop-protection.$$ 2>/tmp/github-develop-protection.err.$$; then
  cat /tmp/github-develop-protection.$$ | json_pp > "${OUTPUT_DIR}/develop-protection.json"
else
  cp /tmp/github-develop-protection.err.$$ "${OUTPUT_DIR}/develop-protection-error.txt"
fi

if gh pr view 1 --repo "${REPO_SLUG}" --json number,title,state,isDraft,headRefName,baseRefName,statusCheckRollup,url >/tmp/github-pr1.$$ 2>/tmp/github-pr1.err.$$; then
  cat /tmp/github-pr1.$$ | json_pp > "${OUTPUT_DIR}/pr-1.json"
else
  cp /tmp/github-pr1.err.$$ "${OUTPUT_DIR}/pr-1-error.txt"
fi

rm -f /tmp/github-rulesets.$$ /tmp/github-rulesets.err.$$ \
  /tmp/github-main-protection.$$ /tmp/github-main-protection.err.$$ \
  /tmp/github-develop-protection.$$ /tmp/github-develop-protection.err.$$ \
  /tmp/github-pr1.$$ /tmp/github-pr1.err.$$

log "Done."
