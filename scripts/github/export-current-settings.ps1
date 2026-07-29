Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
  [string]$GitHubOrg = $env:GITHUB_ORG,
  [string]$GitHubRepo = $env:GITHUB_REPO,
  [string]$OutputDir = $env:OUTPUT_DIR
)

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "Missing gh CLI." }
if ([string]::IsNullOrWhiteSpace($GitHubOrg) -or [string]::IsNullOrWhiteSpace($GitHubRepo)) { throw "Set GITHUB_ORG and GITHUB_REPO." }
if ([string]::IsNullOrWhiteSpace($OutputDir)) { $OutputDir = ".tmp/github-export-$(Get-Date -Format 'yyyyMMdd-HHmmss')" }

$repoSlug = "$GitHubOrg/$GitHubRepo"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

gh api "repos/$repoSlug" | Out-File -Encoding utf8 "$OutputDir/repo.json"
gh api "repos/$repoSlug/branches" | Out-File -Encoding utf8 "$OutputDir/branches.json"
gh api "repos/$repoSlug/actions/permissions" | Out-File -Encoding utf8 "$OutputDir/actions-permissions.json"
gh api "repos/$repoSlug/actions/permissions/workflow" | Out-File -Encoding utf8 "$OutputDir/workflow-permissions.json"
gh api "repos/$repoSlug/actions/secrets" | Out-File -Encoding utf8 "$OutputDir/secrets.json"
gh api "repos/$repoSlug/hooks" | Out-File -Encoding utf8 "$OutputDir/hooks.json"
gh api "repos/$repoSlug/labels?per_page=100" | Out-File -Encoding utf8 "$OutputDir/labels.json"
gh api "orgs/$GitHubOrg/teams?per_page=100" | Out-File -Encoding utf8 "$OutputDir/teams.json"
