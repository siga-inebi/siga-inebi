#!/usr/bin/env sh
set -eu

. "$(dirname "$0")/_common.sh"

require_command gh
require_command python3
require_gh_auth
set_repo_context

cat <<EOF
Ruleset/branch-protection plan for ${REPO_SLUG}
- develop: PR required, 1 approval, stale approvals dismissed, conversations resolved,
  linear history, no force push, no delete, required checks:
  backend-lint, backend-tests, backend-security, frontend-lint, frontend-tests,
  frontend-build, docker-integration, pr-validation
- main: PR required, 2 approvals, CODEOWNERS, stale approvals dismissed,
  latest change approval when available, conversations resolved, linear history,
  no force push, no delete, required checks:
  backend-lint, backend-tests, backend-security, frontend-lint, frontend-tests,
  frontend-build, docker-integration, pr-validation
EOF

if ! gh api "repos/${REPO_SLUG}/rulesets" >/dev/null 2>&1; then
  fail "Repository rulesets unavailable on current plan. GitHub returned 403 earlier for this private repository."
fi

require_apply_ack

fail "Ruleset application intentionally blocked until exact payload is approved."
