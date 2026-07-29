Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
  [string]$GitHubOrg = $env:GITHUB_ORG,
  [string]$GitHubRepo = $env:GITHUB_REPO,
  [string]$Apply = $env:APPLY
)

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "Missing gh CLI." }
if ([string]::IsNullOrWhiteSpace($GitHubOrg) -or [string]::IsNullOrWhiteSpace($GitHubRepo)) { throw "Set GITHUB_ORG and GITHUB_REPO." }

$repoSlug = "$GitHubOrg/$GitHubRepo"
Write-Host "PLAN repo $repoSlug -> default branch develop, keep private, issues/projects on, wiki/discussions off, squash only, read workflow permissions, PR approval by Actions off."

if ($Apply -ne "true") {
  Write-Host "Dry-run only. Use APPLY=true to change GitHub."
  exit 0
}

gh api --method PATCH "repos/$repoSlug" `
  -f default_branch="develop" `
  -F private=true `
  -F has_issues=true `
  -F has_projects=true `
  -F has_wiki=false `
  -F has_discussions=false `
  -F allow_squash_merge=true `
  -F allow_merge_commit=false `
  -F allow_rebase_merge=false `
  -F delete_branch_on_merge=true `
  -F allow_auto_merge=false | Out-Null

gh api --method PUT "repos/$repoSlug/actions/permissions" `
  -f enabled=true `
  -f allowed_actions="all" | Out-Null

gh api --method PUT "repos/$repoSlug/actions/permissions/workflow" `
  -f default_workflow_permissions="read" `
  -F can_approve_pull_request_reviews=false | Out-Null
