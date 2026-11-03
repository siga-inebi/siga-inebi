#!/usr/bin/env sh
# Shared preflight for the scripts that write to GitHub.
#
# These scripts perform hundreds of write calls in a row. Discovering on call 8
# that the active `gh` account only has read access wastes the run and leaves the
# repository half populated, so the check happens once, up front.
#
# Source after set_repo_context.

# Pin the run to one gh account.
#
# A run performs hundreds of write calls over 10-15 minutes. `gh` resolves the
# credential from the *active* account on every call, so a `gh auth switch` in
# another terminal mid-run makes the rest of the calls fail with a permission
# error. Exporting GH_TOKEN overrides that resolution for the whole run.
#
#   GH_ACCOUNT=daniel-baf APPLY=true sh scripts/requirements/create-issues.sh
pin_account() {
  [ -n "${GH_ACCOUNT:-}" ] || return 0
  [ -z "${GH_TOKEN:-}" ] || return 0

  token=$(gh auth token --user "${GH_ACCOUNT}" 2>/dev/null || true)
  [ -n "${token}" ] || fail "$(printf '%s\n' \
    "No stored credential for gh account '${GH_ACCOUNT}'." \
    "  Available: $(gh auth status 2>&1 | sed -n 's/.*account \([^ ]*\).*/\1/p' | paste -sd, -)")"

  GH_TOKEN="${token}"
  export GH_TOKEN
  log "Pinned this run to gh account ${GH_ACCOUNT}; a concurrent auth switch cannot break it."
}

require_write_access() {
  permission=$(gh repo view "${REPO_SLUG}" --json viewerPermission \
    --jq '.viewerPermission' 2>/dev/null || true)
  account=$(gh api user --jq '.login' 2>/dev/null || printf '?')

  if [ -z "${permission}" ]; then
    fail "$(printf '%s\n' \
      "The active gh account (${account}) cannot see ${REPO_SLUG}." \
      "  - If the repository is private and belongs to another account," \
      "    switch to it: gh auth switch --user <owner>" \
      "  - If it does not exist yet, create it first.")"
  fi

  case "${permission}" in
    WRITE | ADMIN | MAINTAIN) ;;
    *)
      fail "$(printf '%s\n' \
        "The active gh account (${account}) has ${permission} access to ${REPO_SLUG}; writing issues needs WRITE." \
        "  Switch account:  gh auth switch --user <account-with-write>" \
        "  Then re-run this script. Nothing has been written.")"
      ;;
  esac

  log "Active account ${account} has ${permission} access to ${REPO_SLUG}."
}
