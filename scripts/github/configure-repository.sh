#!/usr/bin/env sh
set -eu

. "$(dirname "$0")/_common.sh"

require_command gh
require_gh_auth
set_repo_context

cat <<EOF
Repository configuration plan for ${REPO_SLUG}
- Visibility: keep private
- Default branch: develop
- Issues: enabled
- Projects: enabled
- Wiki: disabled
- Discussions: disabled
- Squash merge: enabled
- Merge commits: disabled
- Rebase merge: disabled
- Delete head branches: enabled
- Auto merge: disabled
- Actions workflow permissions: read
- Actions approve PRs: disabled
EOF

[ "${APPLY:-false}" = "true" ] || {
  log "Dry-run only. Re-run with APPLY=true to change GitHub."
  exit 0
}

gh api --method PATCH "repos/${REPO_SLUG}" \
  -f default_branch="develop" \
  -F private=true \
  -F has_issues=true \
  -F has_projects=true \
  -F has_wiki=false \
  -F has_discussions=false \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true \
  -F allow_auto_merge=false >/dev/null

gh api --method PUT "repos/${REPO_SLUG}/actions/permissions" \
  -f enabled=true \
  -f allowed_actions="all" >/dev/null

gh api --method PUT "repos/${REPO_SLUG}/actions/permissions/workflow" \
  -f default_workflow_permissions="read" \
  -F can_approve_pull_request_reviews=false >/dev/null

log "Repository settings updated."
