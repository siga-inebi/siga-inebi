Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
  [string]$GitHubOrg = $env:GITHUB_ORG,
  [string]$GitHubRepo = $env:GITHUB_REPO
)

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "Missing gh CLI." }
if ([string]::IsNullOrWhiteSpace($GitHubOrg) -or [string]::IsNullOrWhiteSpace($GitHubRepo)) { throw "Set GITHUB_ORG and GITHUB_REPO." }

$repoSlug = "$GitHubOrg/$GitHubRepo"
Write-Host "Verify current repository config for $repoSlug"
gh repo view $repoSlug --json nameWithOwner,defaultBranchRef,visibility,mergeCommitAllowed,rebaseMergeAllowed,squashMergeAllowed,deleteBranchOnMerge,hasIssuesEnabled,hasProjectsEnabled,hasWikiEnabled,hasDiscussionsEnabled
gh pr view 1 --repo $repoSlug --json state,baseRefName,statusCheckRollup
