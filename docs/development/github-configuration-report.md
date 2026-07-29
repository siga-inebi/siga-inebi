# GitHub Configuration Report

Fecha de inspeccion: 2026-07-29
Estado de aplicacion: solo inspeccion y preparacion local. No se aplicaron cambios remotos.

## Estado anterior

- Cuenta autenticada en `github.com`: `Crono19`
- Organizacion: `siga-inebi`
- Repositorio: `siga-inebi/siga-inebi`
- Permiso del usuario actual en repo: `ADMIN`
- Rol del usuario actual en organizacion: `admin`
- Rama local actual: `chore/repository-foundation`
- Arbol Git local: limpio
- URL remota: `https://github.com/siga-inebi/siga-inebi.git`

## Workflows y checks confirmados

PR inspeccionado: `#1`

- Estado PR: `MERGED`
- Base: `develop`
- Checks observados en verde:
  - `backend-lint`
  - `backend-tests`
  - `backend-security`
  - `frontend-lint`
  - `frontend-tests`
  - `frontend-build`
  - `docker-integration`
  - `pr-validation`
  - `codeql-analyze (python)`
  - `codeql-analyze (javascript)`
  - `dependency-review`
  - `docker-build`
  - `labeler`

Checks propuestos como obligatorios:

- `backend-lint`
- `backend-tests`
- `backend-security`
- `frontend-lint`
- `frontend-tests`
- `frontend-build`
- `docker-integration`
- `pr-validation`

Checks propuestos como informativos:

- `codeql-analyze (python)`
- `codeql-analyze (javascript)`
- `dependency-review`
- `docker-build`
- `labeler`
- `gga-review` cuando exista uso real

## Configuracion general actual

- Visibilidad: `PRIVATE`
- Rama predeterminada: `main`
- Issues: habilitado
- Projects: habilitado
- Wiki: deshabilitado
- Discussions: deshabilitado
- Squash merge: habilitado
- Merge commits: deshabilitado
- Rebase merge: deshabilitado
- Delete head branches on merge: habilitado
- Auto merge: deshabilitado

## Actions actual

- Actions habilitadas: si
- Politica de Actions: `all`
- Workflow permissions: `read`
- Actions pueden aprobar PRs: no

## Ramas actuales

- `develop`
- `main`

Estado observado:

- `main`: no protegida
- `develop`: no protegida
- Rulesets: no configurados

## Labels actuales

Labels personalizados ya presentes:

- `area:backend`
- `area:database`
- `area:devops`
- `area:docker`
- `area:frontend`
- `area:requirements`
- `area:security`
- `type:chore`
- `type:docs`
- `type:test`

Labels faltantes segun propuesta:

- `type:feature`
- `type:bug`
- `type:refactor`
- `priority:critical`
- `priority:high`
- `priority:medium`
- `priority:low`
- `status:blocked`
- `status:needs-review`
- `breaking-change`
- `security`
- `dependencies`

## Equipos y colaboradores

- Teams actuales en organizacion: ninguno
- Colaboradores visibles en repo:
  - `Crono19` con `admin`
- Miembros visibles en organizacion:
  - `Crono19`

Observacion:

- Con datos inspeccionados hoy, solo se observa una persona en organizacion y repo.
- No pude confirmar existencia de otra cuenta `Owner` distinta. El usuario actual aparece con rol `admin` de organizacion.

## Webhooks, apps y secrets

- Webhooks del repo: ninguno
- Secrets del repo: ninguno
- Environments del repo: ninguno
- GitHub Apps instaladas en repo: no se obtuvo listado util por API inspeccionada

## Seguridad y disponibilidad

| Funcion | Estado |
|---|---|
| Dependency graph / SBOM | no confirmado por API inspeccionada; endpoint usado devolvio `404` |
| Dependabot alerts | disponible como producto, actualmente `Disabled` |
| Dependabot security updates / automated security fixes | `Disabled` |
| Secret scanning | `Disabled` |
| Push protection | no confirmado; normalmente depende de Secret Scanning / plan |
| Code scanning | requiere GitHub Advanced Security; hoy no habilitado |
| Dependency Review | disponible y funcionando via workflow |
| Private vulnerability reporting | no confirmado por endpoint usado; requiere verificacion manual en UI |

## Limitaciones del plan o licencia detectadas

- `rulesets`: GitHub devolvio `403 Upgrade to GitHub Pro or make this repository public to enable this feature`
- `branch protection`: mismo `403` anterior en repo privado actual
- `code scanning alerts`: `403 Advanced Security must be enabled`
- `projectsV2` por GraphQL: token actual no tiene scope `read:project`

## Propuesta de configuracion remota

### Configuracion general

- Mantener visibilidad `Private`
- Cambiar rama predeterminada a `develop`
- Mantener `Issues` habilitado
- Mantener `Projects` habilitado
- Mantener `Wiki` deshabilitado
- Mantener `Discussions` deshabilitado por ahora
- Mantener `Squash merge` habilitado
- Mantener `Merge commits` deshabilitado
- Mantener `Rebase merge` deshabilitado por ahora
- Mantener `Delete head branches` habilitado
- Mantener `Auto merge` deshabilitado por ahora

### Equipos propuestos

- `project-management`: `maintain` o `write`
- `backend`: `write`
- `frontend`: `write`
- `qa`: `write` o `triage`
- `devops`: `write`
- `security`: `triage` o `write`
- `analysis`: `triage` o `write`

Notas:

- No otorgar `Owner` ni `Admin` general a otros miembros
- Cambios criticos protegidos por CODEOWNERS y aprobacion de responsable

### Proteccion propuesta para `develop`

- PR obligatorio
- 1 aprobacion
- descartar aprobaciones obsoletas
- resolver conversaciones
- bloquear force push
- bloquear eliminacion
- historial lineal
- checks obligatorios:
  - `backend-lint`
  - `backend-tests`
  - `backend-security`
  - `frontend-lint`
  - `frontend-tests`
  - `frontend-build`
  - `docker-integration`
  - `pr-validation`
- checks informativos:
  - `dependency-review`
  - `codeql-analyze (python)`
  - `codeql-analyze (javascript)`
  - `docker-build`
  - `labeler`

### Proteccion propuesta para `main`

- PR obligatorio
- 2 aprobaciones
- CODEOWNERS
- descartar aprobaciones obsoletas
- resolver conversaciones
- aprobacion del cambio mas reciente cuando opcion exista
- bloquear force push
- bloquear eliminacion
- historial lineal
- checks obligatorios:
  - `backend-lint`
  - `backend-tests`
  - `backend-security`
  - `frontend-lint`
  - `frontend-tests`
  - `frontend-build`
  - `docker-integration`
  - `pr-validation`

### Hotfix propuesto

1. Crear branch `hotfix/...` desde `main`
2. Abrir PR hacia `main`
3. Mantener checks obligatorios
4. Owner o responsable autorizado hace merge squash
5. Abrir PR de retroalimentacion `main -> develop` si aplica

## Scripts preparados

- `scripts/github/export-current-settings.sh`
- `scripts/github/verify-configuration.sh`
- `scripts/github/configure-labels.sh`
- `scripts/github/configure-repository.sh`
- `scripts/github/configure-rulesets.sh`
- `scripts/github/export-current-settings.ps1`
- `scripts/github/verify-configuration.ps1`
- `scripts/github/configure-labels.ps1`
- `scripts/github/configure-repository.ps1`
- `scripts/github/configure-rulesets.ps1`

Comportamiento:

- Validan `gh`
- No usan tokens hardcodeados
- Aceptan `GITHUB_ORG` y `GITHUB_REPO`
- Trabajan en dry-run por defecto
- Solo aplican con `APPLY=true`
- `configure-rulesets*` bloquea aplicacion mientras no exista soporte de plan y aprobacion explicita

## Plan antes de aplicar

1. Confirmar si repo/plan soporta rulesets o branch protection en privado
2. Confirmar si quieres usar proteccion clasica como fallback si rulesets no estan disponibles
3. Crear equipos de organizacion
4. Completar labels faltantes
5. Cambiar rama predeterminada a `develop`
6. Aplicar protecciones/rulesets segun soporte real
7. Verificar settings finales

## Riesgos pendientes

- Si el plan actual no soporta rulesets ni branch protection en repo privado, no se podra cerrar completamente esta fase sin cambiar plan o estrategia
- El usuario actual aparece como `admin` en organizacion; hace falta confirmar en UI que exista solo una `Owner`
- `CODEOWNERS` aun usa placeholder `@ORGANIZATION/...`; no debe hacerse obligatorio hasta reemplazarlo por slugs reales
- `projectsV2` no pudo inspeccionarse por falta de scope `read:project`
- Features de seguridad avanzadas pueden requerir GitHub Advanced Security o plan superior
