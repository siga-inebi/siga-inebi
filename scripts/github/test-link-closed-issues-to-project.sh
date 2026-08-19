#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
WORK_DIR=$(mktemp -d)
trap 'rm -rf "${WORK_DIR}"' EXIT

cat >"${WORK_DIR}/gh" <<'EOF'
#!/usr/bin/env sh
set -eu

case "$*" in
  "auth status")
    exit 0
    ;;
  "issue list --repo test/repo --state closed --limit 1000 --json number,url")
    if [ "${GH_SCENARIO:-missing}" = "closed-truncated" ]; then
      printf '%s\n' '[{"number":1,"url":"https://github.com/test/repo/issues/1"}]'
    else
      printf '%s\n' '[{"number":1,"url":"https://github.com/test/repo/issues/1"},{"number":2,"url":"https://github.com/test/repo/issues/2"}]'
    fi
    ;;
  "project item-list 7 --owner test --limit 1000 --format json")
    case "${GH_SCENARIO:-missing}" in
      all-linked)
        printf '%s\n' '{"totalCount":2,"items":[{"content":{"url":"https://github.com/test/repo/issues/1"}},{"content":{"url":"https://github.com/test/repo/issues/2"}}]}'
        ;;
      project-truncated)
        printf '%s\n' '{"totalCount":2,"items":[{"content":{"url":"https://github.com/test/repo/issues/1"}}]}'
        ;;
      *)
        printf '%s\n' '{"totalCount":1,"items":[{"content":{"url":"https://github.com/test/repo/issues/1"}}]}'
        ;;
    esac
    ;;
  "api graphql -f query=query(\$owner:String!,\$name:String!){repository(owner:\$owner,name:\$name){issues(states:CLOSED){totalCount}}} -F owner=test -F name=repo --jq .data.repository.issues.totalCount")
    printf '%s\n' '2'
    ;;
  "project item-add 7 --owner test --url https://github.com/test/repo/issues/2")
    printf '%s\n' "$*" >>"${GH_CALLS}"
    ;;
  *)
    printf 'Unexpected gh call: %s\n' "$*" >&2
    exit 1
    ;;
esac
EOF
chmod +x "${WORK_DIR}/gh"

export PATH="${WORK_DIR}:${PATH}"
export REPO_SLUG="test/repo"
export PROJECT_OWNER="test"
export PROJECT_NUMBER="7"
export GH_CALLS="${WORK_DIR}/calls"

dry_run=$(sh "${SCRIPT_DIR}/link-closed-issues-to-project.sh")
printf '%s\n' "${dry_run}" | grep -F "LINK #2 https://github.com/test/repo/issues/2" >/dev/null
printf '%s\n' "${dry_run}" | grep -F "1 closed issues would be linked" >/dev/null
[ ! -e "${GH_CALLS}" ]

APPLY=true sh "${SCRIPT_DIR}/link-closed-issues-to-project.sh" >/dev/null
[ "$(wc -l <"${GH_CALLS}" | tr -d ' ')" -eq 1 ]
grep -F "project item-add 7 --owner test --url https://github.com/test/repo/issues/2" "${GH_CALLS}" >/dev/null

rm -f "${GH_CALLS}"
GH_SCENARIO=all-linked APPLY=true sh "${SCRIPT_DIR}/link-closed-issues-to-project.sh" >/dev/null
[ ! -e "${GH_CALLS}" ]

for scenario in closed-truncated project-truncated; do
  rm -f "${GH_CALLS}"
  if GH_SCENARIO=${scenario} APPLY=true sh "${SCRIPT_DIR}/link-closed-issues-to-project.sh" >"${WORK_DIR}/${scenario}.out" 2>&1; then
    printf 'Expected %s list to fail closed\n' "${scenario}" >&2
    exit 1
  fi
  grep -F "list was truncated" "${WORK_DIR}/${scenario}.out" >/dev/null
  [ ! -e "${GH_CALLS}" ]
done

printf '%s\n' "PASS: link-closed-issues-to-project.sh"
