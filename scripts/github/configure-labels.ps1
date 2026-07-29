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
$labels = @(
  @{ name="type:feature"; color="0e8a16"; description="Trabajo funcional nuevo." },
  @{ name="type:bug"; color="d73a4a"; description="Correccion de defecto." },
  @{ name="type:test"; color="1d76db"; description="Cambios de pruebas y calidad." },
  @{ name="type:docs"; color="0075ca"; description="Cambios de documentacion." },
  @{ name="type:refactor"; color="5319e7"; description="Refactor sin cambio funcional esperado." },
  @{ name="type:chore"; color="6e7781"; description="Mantenimiento tecnico." },
  @{ name="area:frontend"; color="fbca04"; description="Frontend React/Vite." },
  @{ name="area:backend"; color="bfd4f2"; description="Backend Django/DRF." },
  @{ name="area:database"; color="c5def5"; description="Modelo, migraciones o PostgreSQL." },
  @{ name="area:docker"; color="0e8a16"; description="Docker y Compose." },
  @{ name="area:security"; color="b60205"; description="Seguridad y autorizacion." },
  @{ name="area:devops"; color="1d76db"; description="CI/CD, GitHub y automatizacion." },
  @{ name="area:requirements"; color="d4c5f9"; description="Requerimientos y analisis." },
  @{ name="priority:critical"; color="b60205"; description="Impacto critico." },
  @{ name="priority:high"; color="d93f0b"; description="Alta prioridad." },
  @{ name="priority:medium"; color="fbca04"; description="Prioridad media." },
  @{ name="priority:low"; color="0e8a16"; description="Prioridad baja." },
  @{ name="status:blocked"; color="000000"; description="Trabajo bloqueado." },
  @{ name="status:needs-review"; color="5319e7"; description="Listo para revision." },
  @{ name="breaking-change"; color="b60205"; description="Cambio incompatible." },
  @{ name="security"; color="b60205"; description="Seguimiento de seguridad." },
  @{ name="dependencies"; color="0366d6"; description="Dependencias y actualizaciones." }
)

foreach ($label in $labels) {
  Write-Host "PLAN label $($label.name)"
}

if ($Apply -ne "true") {
  Write-Host "Dry-run only. Use APPLY=true to change GitHub."
  exit 0
}

foreach ($label in $labels) {
  gh label create $label.name --repo $repoSlug --color $label.color --description $label.description --force | Out-Null
}
