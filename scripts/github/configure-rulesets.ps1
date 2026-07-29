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
Write-Host "PLAN rulesets for $repoSlug"
Write-Host "Current known limitation: private repo returns 403 for rulesets/branch protection on current plan."

if ($Apply -ne "true") {
  Write-Host "Dry-run only. Use APPLY=true after plan support is confirmed."
  exit 0
}

throw "Ruleset apply blocked until plan support and payload are explicitly approved."
