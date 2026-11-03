#!/usr/bin/env sh
set -eu

. "$(dirname "$0")/_common.sh"

require_command gh
require_command python3
require_gh_auth
set_repo_context

TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR}"' EXIT

gh_api "repos/${REPO_SLUG}" > "${TMP_DIR}/repo.json"
gh_api "repos/${REPO_SLUG}/actions/permissions" > "${TMP_DIR}/actions.json"
gh_api "repos/${REPO_SLUG}/actions/permissions/workflow" > "${TMP_DIR}/workflow.json"
gh_api "repos/${REPO_SLUG}/labels?per_page=100" > "${TMP_DIR}/labels.json"
gh pr view 1 --repo "${REPO_SLUG}" --json statusCheckRollup,state,baseRefName > "${TMP_DIR}/pr1.json"

python3 - "${TMP_DIR}" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
repo = json.loads((root / "repo.json").read_text())
actions = json.loads((root / "actions.json").read_text())
workflow = json.loads((root / "workflow.json").read_text())
labels = {item["name"] for item in json.loads((root / "labels.json").read_text())}
pr1 = json.loads((root / "pr1.json").read_text())

required_checks = {
    "backend-lint",
    "backend-tests",
    "backend-security",
    "frontend-lint",
    "frontend-tests",
    "frontend-build",
    "docker-integration",
    "pr-validation",
}
observed_checks = {item["name"] for item in pr1["statusCheckRollup"]}
desired_labels = {
    "type:feature",
    "type:bug",
    "type:test",
    "type:docs",
    "type:refactor",
    "type:chore",
    "area:frontend",
    "area:backend",
    "area:database",
    "area:docker",
    "area:security",
    "area:devops",
    "area:requirements",
    "priority:critical",
    "priority:high",
    "priority:medium",
    "priority:low",
    "status:blocked",
    "status:needs-review",
    "breaking-change",
    "security",
    "dependencies",
}

checks = [
    ("repo private", repo["private"] is True, str(repo["private"])),
    ("default branch develop", repo["default_branch"] == "develop", repo["default_branch"]),
    ("issues enabled", repo["has_issues"] is True, str(repo["has_issues"])),
    ("projects enabled", repo["has_projects"] is True, str(repo["has_projects"])),
    ("wiki disabled", repo["has_wiki"] is False, str(repo["has_wiki"])),
    ("discussions disabled", repo["has_discussions"] is False, str(repo["has_discussions"])),
    ("squash merge enabled", repo["allow_squash_merge"] is True, str(repo["allow_squash_merge"])),
    ("merge commit disabled", repo["allow_merge_commit"] is False, str(repo["allow_merge_commit"])),
    ("rebase merge disabled", repo["allow_rebase_merge"] is False, str(repo["allow_rebase_merge"])),
    ("delete branch on merge enabled", repo["delete_branch_on_merge"] is True, str(repo["delete_branch_on_merge"])),
    ("auto merge disabled", repo["allow_auto_merge"] is False, str(repo["allow_auto_merge"])),
    ("actions enabled", actions["enabled"] is True, str(actions["enabled"])),
    ("actions allowed all", actions["allowed_actions"] == "all", actions["allowed_actions"]),
    ("workflow permissions read", workflow["default_workflow_permissions"] == "read", workflow["default_workflow_permissions"]),
    ("actions cannot approve PRs", workflow["can_approve_pull_request_reviews"] is False, str(workflow["can_approve_pull_request_reviews"])),
    ("PR #1 merged into develop", pr1["state"] == "MERGED" and pr1["baseRefName"] == "develop", f"{pr1['state']}->{pr1['baseRefName']}"),
    ("required checks observed", required_checks.issubset(observed_checks), ", ".join(sorted(observed_checks))),
    ("all planned labels exist", desired_labels.issubset(labels), ", ".join(sorted(desired_labels - labels)) or "all present"),
]

failed = False
for name, ok, detail in checks:
    state = "PASS" if ok else "FAIL"
    print(f"{state}: {name} [{detail}]")
    failed = failed or not ok

sys.exit(1 if failed else 0)
PY
