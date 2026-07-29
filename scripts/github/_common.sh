#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

log() {
  printf '%s\n' "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"
}

require_gh_auth() {
  gh auth status >/dev/null 2>&1 || fail "GitHub CLI not authenticated."
}

repo_slug_from_git() {
  remote_url=$(git remote get-url origin 2>/dev/null || true)
  [ -n "${remote_url}" ] || return 1
  printf '%s' "${remote_url}" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##'
}

set_repo_context() {
  if [ -n "${GITHUB_ORG:-}" ] && [ -n "${GITHUB_REPO:-}" ]; then
    REPO_SLUG="${GITHUB_ORG}/${GITHUB_REPO}"
    return 0
  fi

  slug=$(repo_slug_from_git || true)
  [ -n "${slug}" ] || fail "Set GITHUB_ORG and GITHUB_REPO."
  GITHUB_ORG=$(printf '%s' "${slug}" | cut -d/ -f1)
  GITHUB_REPO=$(printf '%s' "${slug}" | cut -d/ -f2)
  REPO_SLUG="${GITHUB_ORG}/${GITHUB_REPO}"
}

require_apply_ack() {
  [ "${APPLY:-false}" = "true" ] || fail "Dry-run only. Re-run with APPLY=true to change GitHub."
}

gh_api() {
  gh api "$@"
}

json_pp() {
  python3 -m json.tool
}
