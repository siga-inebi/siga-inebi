#!/usr/bin/env sh
set -eu

. "$(dirname "$0")/_common.sh"

require_command gh
require_command python3
require_gh_auth
set_repo_context

log "Preparing labels for ${REPO_SLUG}"
log "Dry-run by default. Use APPLY=true to change GitHub."

create_or_update_label() {
  name="$1"
  color="$2"
  description="$3"
  encoded_name=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "${name}")

  if gh_api "repos/${REPO_SLUG}/labels/${encoded_name}" >/dev/null 2>&1; then
    log "UPDATE label ${name} (${color})"
    [ "${APPLY:-false}" = "true" ] && gh api \
      --method PATCH \
      "repos/${REPO_SLUG}/labels/${encoded_name}" \
      -f new_name="${name}" \
      -f color="${color}" \
      -f description="${description}" >/dev/null
  else
    log "CREATE label ${name} (${color})"
    [ "${APPLY:-false}" = "true" ] && gh api \
      --method POST \
      "repos/${REPO_SLUG}/labels" \
      -f name="${name}" \
      -f color="${color}" \
      -f description="${description}" >/dev/null
  fi
}

create_or_update_label "type:feature" "0e8a16" "Trabajo funcional nuevo."
create_or_update_label "type:bug" "d73a4a" "Correccion de defecto."
create_or_update_label "type:test" "1d76db" "Cambios de pruebas y calidad."
create_or_update_label "type:docs" "0075ca" "Cambios de documentacion."
create_or_update_label "type:refactor" "5319e7" "Refactor sin cambio funcional esperado."
create_or_update_label "type:chore" "6e7781" "Mantenimiento tecnico."
create_or_update_label "area:frontend" "fbca04" "Frontend React/Vite."
create_or_update_label "area:backend" "bfd4f2" "Backend Django/DRF."
create_or_update_label "area:database" "c5def5" "Modelo, migraciones o PostgreSQL."
create_or_update_label "area:docker" "0e8a16" "Docker y Compose."
create_or_update_label "area:security" "b60205" "Seguridad y autorizacion."
create_or_update_label "area:devops" "1d76db" "CI/CD, GitHub y automatizacion."
create_or_update_label "area:requirements" "d4c5f9" "Requerimientos y analisis."
create_or_update_label "priority:critical" "b60205" "Impacto critico."
create_or_update_label "priority:high" "d93f0b" "Alta prioridad."
create_or_update_label "priority:medium" "fbca04" "Prioridad media."
create_or_update_label "priority:low" "0e8a16" "Prioridad baja."
create_or_update_label "status:blocked" "000000" "Trabajo bloqueado."
create_or_update_label "status:needs-review" "5319e7" "Listo para revision."
create_or_update_label "breaking-change" "b60205" "Cambio incompatible."
create_or_update_label "security" "b60205" "Seguimiento de seguridad."
create_or_update_label "dependencies" "0366d6" "Dependencias y actualizaciones."

[ "${APPLY:-false}" = "true" ] || log "No remote changes applied."
