#!/usr/bin/env sh
# Add the completed course weeks S1-S8 as dated summary items in GitHub Project #1.
#
#   sh scripts/github/add-completed-course-weeks-to-project.sh
#   APPLY=true sh scripts/github/add-completed-course-weeks-to-project.sh
#
# Activities are summarized from pages 3-5 of "Proyectos de Ingeniería en
# Informática y Sistemas, 2603.pdf" (URL, second semester 2026, section 01).
# Dates use seven-day intervals whose boundaries are shared by adjacent weeks.
# S8 therefore ends on 2026-08-13, the same date on which S9 starts.
set -eu

# shellcheck source=_common.sh
. "$(dirname "$0")/_common.sh"

require_command gh
require_command jq
require_gh_auth

PROJECT_OWNER="${PROJECT_OWNER:-siga-inebi}"
PROJECT_NUMBER="${PROJECT_NUMBER:-1}"
START_FIELD_NAME="${START_FIELD_NAME:-Fecha inicio}"
END_FIELD_NAME="${END_FIELD_NAME:-Fecha esperada}"

WORK_DIR=$(mktemp -d)
trap 'rm -rf "${WORK_DIR}"' EXIT

FIELDS_JSON="${WORK_DIR}/fields.json"
ITEMS_JSON="${WORK_DIR}/items.json"
WEEKS_TSV="${WORK_DIR}/weeks.tsv"
RESOLVED_WEEKS_TSV="${WORK_DIR}/resolved-weeks.tsv"
TAB=$(printf '\t')

cat >"${WEEKS_TSV}" <<'EOF'
S1	2026-06-18	2026-06-25	S1 · Inicio y organización del proyecto	Equipo conformado, herramientas colaborativas configuradas, repositorio organizado y expediente digital iniciado.
S2	2026-06-25	2026-07-02	S2 · Institución, problema y formalización	Institución beneficiaria y problema identificados; factibilidad, acta de constitución, cronograma preliminar y plan de comunicación preparados.
S3	2026-07-02	2026-07-09	S3 · Levantamiento y proceso actual	Entrevistas, observación, partes interesadas, proceso AS-IS y necesidades principales documentados.
S4	2026-07-09	2026-07-16	S4 · Requerimientos y alcance	Requerimientos funcionales y no funcionales, reglas de negocio, alcance, historias de usuario y criterios de aceptación definidos.
S5	2026-07-16	2026-07-23	S5 · Priorización, trazabilidad y validación	Funcionalidades priorizadas, matriz de trazabilidad creada y análisis validado con la institución.
S6	2026-07-23	2026-07-30	S6 · Modelado UML del sistema	Casos de uso, actividades y secuencias modelados y contrastados con los requerimientos.
S7	2026-07-30	2026-08-06	S7 · Arquitectura y diseño lógico de datos	Arquitectura, componentes, tecnologías, modelo conceptual, modelo lógico y diccionario preliminar definidos.
S8	2026-08-06	2026-08-13	S8 · Diseño físico, interfaces y validación	Modelo físico, scripts iniciales, prototipos de interfaz y documento de diseño validados antes del desarrollo.
EOF

project_id=$(gh project view "${PROJECT_NUMBER}" \
  --owner "${PROJECT_OWNER}" \
  --format json \
  --jq '.id')

gh project field-list "${PROJECT_NUMBER}" \
  --owner "${PROJECT_OWNER}" \
  --limit 1000 \
  --format json >"${FIELDS_JSON}"

gh project item-list "${PROJECT_NUMBER}" \
  --owner "${PROJECT_OWNER}" \
  --limit 1000 \
  --format json >"${ITEMS_JSON}"

returned_field_count=$(jq -er '.fields | length' "${FIELDS_JSON}")
total_field_count=$(jq -er '.totalCount' "${FIELDS_JSON}")
[ "${returned_field_count}" -eq "${total_field_count}" ] ||
  fail "Project field list was truncated: received ${returned_field_count} of ${total_field_count} fields"

returned_item_count=$(jq -er '.items | length' "${ITEMS_JSON}")
total_item_count=$(jq -er '.totalCount' "${ITEMS_JSON}")
[ "${returned_item_count}" -eq "${total_item_count}" ] ||
  fail "Project item list was truncated: received ${returned_item_count} of ${total_item_count} items"

field_id() {
  jq -r --arg name "$1" '.fields[] | select(.name == $name) | .id' "${FIELDS_JSON}"
}

start_field_id=$(field_id "${START_FIELD_NAME}")
end_field_id=$(field_id "${END_FIELD_NAME}")
status_field_id=$(field_id "Status")
done_option_id=$(jq -r '
  .fields[]
  | select(.name == "Status")
  | .options[]
  | select(.name == "Done")
  | .id
' "${FIELDS_JSON}")

[ -n "${end_field_id}" ] || fail "Missing Project date field: ${END_FIELD_NAME}"
[ -n "${status_field_id}" ] || fail "Missing Project field: Status"
[ -n "${done_option_id}" ] || fail "Missing Status option: Done"

item_id_for_title() {
  matching_count=$(jq -r --arg title "$1" '
    [.items[] | select(.content.type == "DraftIssue" and .title == $title)] | length
  ' "${ITEMS_JSON}")

  [ "${matching_count}" -le 1 ] || fail "Multiple Project draft items have title: $1"
  jq -r --arg title "$1" '
    .items[] | select(.content.type == "DraftIssue" and .title == $title) | .id
  ' "${ITEMS_JSON}"
}

log "Project: ${PROJECT_OWNER}/${PROJECT_NUMBER}"
log "Historical boundary: S8 ends and S9 starts on 2026-08-13"

while IFS="${TAB}" read -r week start end title body; do
  item_id=$(item_id_for_title "${title}")
  [ -n "${item_id}" ] || item_id="-"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "${week}" "${start}" "${end}" "${title}" "${body}" "${item_id}" \
    >>"${RESOLVED_WEEKS_TSV}"
done <"${WEEKS_TSV}"

if [ "${APPLY:-false}" != "true" ]; then
  if [ -z "${start_field_id}" ]; then
    log "CREATE FIELD ${START_FIELD_NAME} (DATE)"
  fi

  while IFS="${TAB}" read -r week start end title body item_id; do
    if [ "${item_id}" != "-" ]; then
      action="UPDATE"
    else
      action="CREATE"
    fi
    log "${action} ${week} ${start} -> ${end} [Done] ${title}"
  done <"${RESOLVED_WEEKS_TSV}"

  log "Dry-run complete. Re-run with APPLY=true using an account with Project write access."
  exit 0
fi

if [ -z "${start_field_id}" ]; then
  start_field_id=$(gh project field-create "${PROJECT_NUMBER}" \
    --owner "${PROJECT_OWNER}" \
    --name "${START_FIELD_NAME}" \
    --data-type DATE \
    --format json \
    --jq '.id')
  log "CREATED FIELD ${START_FIELD_NAME}"
fi

while IFS="${TAB}" read -r week start end title body item_id; do
  if [ "${item_id}" = "-" ]; then
    item_id=$(gh project item-create "${PROJECT_NUMBER}" \
      --owner "${PROJECT_OWNER}" \
      --title "${title}" \
      --body "${body}" \
      --format json \
      --jq '.id')
    action="CREATED"
  else
    gh project item-edit \
      --id "${item_id}" \
      --body "${body}" >/dev/null
    action="UPDATED"
  fi

  gh project item-edit \
    --id "${item_id}" \
    --project-id "${project_id}" \
    --field-id "${start_field_id}" \
    --date "${start}" >/dev/null

  gh project item-edit \
    --id "${item_id}" \
    --project-id "${project_id}" \
    --field-id "${end_field_id}" \
    --date "${end}" >/dev/null

  gh project item-edit \
    --id "${item_id}" \
    --project-id "${project_id}" \
    --field-id "${status_field_id}" \
    --single-select-option-id "${done_option_id}" >/dev/null

  log "${action} ${week} ${start} -> ${end} [Done]"
done <"${RESOLVED_WEEKS_TSV}"

log "Complete. S1-S8 are available as completed dated Project items."
