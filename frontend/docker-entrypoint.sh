#!/bin/sh
set -eu

LOCKFILE_PATH="/app/package-lock.json"
NODE_MODULES_PATH="/app/node_modules"
LOCKFILE_HASH_PATH="${NODE_MODULES_PATH}/.package-lock.hash"

ensure_dependencies() {
  if [ ! -f "$LOCKFILE_PATH" ]; then
    return
  fi

  current_hash="$(sha256sum "$LOCKFILE_PATH" | awk '{print $1}')"
  installed_hash=""

  if [ -f "$LOCKFILE_HASH_PATH" ]; then
    installed_hash="$(cat "$LOCKFILE_HASH_PATH")"
  fi

  if [ ! -d "$NODE_MODULES_PATH" ] || [ "$current_hash" != "$installed_hash" ]; then
    echo "Installing frontend dependencies with npm ci..."
    npm ci
    printf '%s' "$current_hash" > "$LOCKFILE_HASH_PATH"
  fi
}

ensure_dependencies

exec "$@"
