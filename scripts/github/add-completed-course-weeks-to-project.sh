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
RESPONSIBLES_FIELD_NAME="${RESPONSIBLES_FIELD_NAME:-Responsables}"

WORK_DIR=$(mktemp -d)
trap 'rm -rf "${WORK_DIR}"' EXIT

FIELDS_JSON="${WORK_DIR}/fields.json"
ITEMS_JSON="${WORK_DIR}/items.json"
WEEKS_TSV="${WORK_DIR}/weeks.tsv"
RESOLVED_WEEKS_TSV="${WORK_DIR}/resolved-weeks.tsv"
TAB=$(printf '\t')

cat >"${WEEKS_TSV}" <<'EOF'
S1	2026-06-18	2026-06-25	S1 · Inicio y organización del proyecto	Equipo SIGA-INEBI	Resumen oficial de S1: organización del curso y del equipo, posible búsqueda de institución, configuración de Jira/GitHub y apertura del expediente digital del proyecto. No se suministró una asignación histórica individual.
S2	2026-06-25	2026-07-02	S2 · Institución, problema y formalización	Equipo SIGA-INEBI	Resumen oficial de S2: selección de la institución, planteamiento preliminar del problema, factibilidad, acta de constitución, cronograma preliminar, comunicación y aprobación para continuar. No se suministró una asignación histórica individual.
S3	2026-07-02	2026-07-09	S3 · Levantamiento y proceso actual	Pablo (Crono); Luis Ovalle; Daniel Bautista; Diana; Roí	Resumen oficial de S3: recopilación de información mediante entrevistas, observaciones y documentos; identificación de interesados; proceso actual AS-IS y necesidades identificadas. Evidencia histórica: visita técnica y levantamiento de requisitos e información. Pablo: plan y guía de entrevista, minuta, observaciones y documentos. Diana: mapa de interesados. Roí: proceso actual AS-IS y propuesta de proceso mejorado. La participación registrada en la visita corresponde a Pablo, Luis y Daniel; Diana conservó la responsabilidad del mapa de interesados.
S4	2026-07-09	2026-07-16	S4 · Requerimientos y alcance	Daniel; Ángel; Luis; Estuardo; Pablo (coordinación)	Resumen oficial de S4: requisitos funcionales y no funcionales, reglas de negocio, alcance, exclusiones, restricciones, supuestos, historias de usuario y criterios de aceptación. Daniel: requisitos funcionales y no funcionales. Ángel: reglas de negocio, alcance, exclusiones, restricciones y supuestos. Luis: historias de usuario y criterios de aceptación. Estuardo: problema definitivo y objetivos general y específicos. Pablo: integración y revisión del documento.
S5	2026-07-16	2026-07-23	S5 · Priorización, trazabilidad y validación	Emilio; Josué; Daniel (coordinación técnica); Pablo (revisión); Luis; Santiago; equipo SIGA-INEBI	Resumen oficial de S5: funciones priorizadas, matriz inicial de trazabilidad, análisis consolidado y validación institucional. Emilio: lista priorizada de funcionalidades. Josué: validación de requisitos con la institución. Trabajo conjunto: primera versión funcional y matriz inicial de trazabilidad. Daniel: coordinación técnica. Pablo: revisión de alineación. La matriz recibió apoyo de Daniel, Luis, Emilio y Santiago. Luis también imprimió y llevó los requisitos para su validación institucional.
S6	2026-07-23	2026-07-30	S6 · Modelado UML del sistema	Equipo SIGA-INEBI	Resumen oficial de S6: casos de uso, actividades y secuencias UML. No se suministró una asignación histórica individual.
S7	2026-07-30	2026-08-06	S7 · Arquitectura y diseño lógico de datos	Equipo SIGA-INEBI	Resumen oficial de S7: arquitectura, tecnologías, modelo conceptual y lógico de datos y diccionario preliminar. No se suministró una asignación histórica individual.
S8	2026-08-06	2026-08-13	S8 · Diseño físico, interfaces y validación	Equipo SIGA-INEBI	Resumen oficial de S8: modelo físico de datos, scripts iniciales, interfaces y prototipos, y validación del diseño. No se suministró una asignación histórica individual.
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

require_unique_configurable_field() {
  field_name=$1
  matching_count=$(jq -r --arg name "${field_name}" \
    '[.fields[] | select(.name == $name)] | length' "${FIELDS_JSON}")
  [ "${matching_count}" -le 1 ] || fail "Multiple Project fields have name: ${field_name}"
}

field_data_type() {
  # shellcheck disable=SC2016 # GraphQL variables must reach GitHub literally.
  gh api graphql \
    -f query='query($id: ID!) { node(id: $id) { ... on ProjectV2Field { dataType } } }' \
    -F id="$1" \
    --jq '.data.node.dataType'
}

require_field_data_type() {
  field_name=$1
  field_id_value=$2
  expected_type=$3
  [ -z "${field_id_value}" ] && return
  actual_type=$(field_data_type "${field_id_value}")
  [ "${actual_type}" = "${expected_type}" ] ||
    fail "Project field ${field_name} must have data type ${expected_type}; found ${actual_type:-unknown}"
}

require_unique_configurable_field "${START_FIELD_NAME}"
require_unique_configurable_field "${END_FIELD_NAME}"
require_unique_configurable_field "${RESPONSIBLES_FIELD_NAME}"

status_field_count=$(jq -r '[.fields[] | select(.name == "Status")] | length' "${FIELDS_JSON}")
[ "${status_field_count}" -gt 0 ] || fail "Missing Project field: Status"
[ "${status_field_count}" -eq 1 ] || fail "Multiple Project fields have name: Status"

status_field_type=$(jq -r '.fields[] | select(.name == "Status") | .type' "${FIELDS_JSON}")
[ "${status_field_type}" = "ProjectV2SingleSelectField" ] ||
  fail "Project field Status must have type ProjectV2SingleSelectField; found ${status_field_type:-unknown}"

done_option_count=$(jq -r '
  [.fields[]
    | select(.name == "Status")
    | (.options // [])[]
    | select(.name == "Done")]
  | length
' "${FIELDS_JSON}")
[ "${done_option_count}" -gt 0 ] || fail "Missing Status option: Done"
[ "${done_option_count}" -eq 1 ] || fail "Multiple Status options have name: Done"

start_field_id=$(field_id "${START_FIELD_NAME}")
end_field_id=$(field_id "${END_FIELD_NAME}")
responsibles_field_id=$(field_id "${RESPONSIBLES_FIELD_NAME}")
status_field_id=$(field_id "Status")
done_option_id=$(jq -r '
  .fields[]
  | select(.name == "Status")
  | .options[]
  | select(.name == "Done")
  | .id
' "${FIELDS_JSON}")

[ -n "${end_field_id}" ] || fail "Missing Project date field: ${END_FIELD_NAME}"

require_field_data_type "${START_FIELD_NAME}" "${start_field_id}" DATE
require_field_data_type "${END_FIELD_NAME}" "${end_field_id}" DATE
require_field_data_type "${RESPONSIBLES_FIELD_NAME}" "${responsibles_field_id}" TEXT

item_id_for_title() {
  title=$1
  marker=$2
  matching_count=$(jq -r --arg title "${title}" '
    [.items[] | select(.content.type == "DraftIssue" and .title == $title)] | length
  ' "${ITEMS_JSON}")

  [ "${matching_count}" -le 1 ] || fail "Multiple Project draft items have title: ${title}"
  if [ "${matching_count}" -eq 1 ]; then
    owned_count=$(jq -r --arg title "${title}" --arg marker "${marker}" '
      [.items[]
        | select(.content.type == "DraftIssue" and .title == $title)
        | select((.body // "") | contains($marker))]
      | length
    ' "${ITEMS_JSON}")
    [ "${owned_count}" -eq 1 ] ||
      fail "Project draft item is not managed by this script: ${title}"
  fi
  jq -r --arg title "${title}" '
    .items[] | select(.content.type == "DraftIssue" and .title == $title) | .id
  ' "${ITEMS_JSON}"
}

log "Project: ${PROJECT_OWNER}/${PROJECT_NUMBER}"
log "Historical boundary: S8 ends and S9 starts on 2026-08-13"

while IFS="${TAB}" read -r week start end title responsibles body; do
  marker="<!-- siga-inebi:course-week:${week} -->"
  body="${body} ${marker}"
  item_id=$(item_id_for_title "${title}" "${marker}")
  [ -n "${item_id}" ] || item_id="-"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "${week}" "${start}" "${end}" "${title}" "${responsibles}" "${body}" "${item_id}" \
    >>"${RESOLVED_WEEKS_TSV}"
done <"${WEEKS_TSV}"

if [ "${APPLY:-false}" != "true" ]; then
  if [ -z "${start_field_id}" ]; then
    log "CREATE FIELD ${START_FIELD_NAME} (DATE)"
  fi
  if [ -z "${responsibles_field_id}" ]; then
    log "CREATE FIELD ${RESPONSIBLES_FIELD_NAME} (TEXT)"
  fi

  while IFS="${TAB}" read -r week start end title responsibles body item_id; do
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

# shellcheck disable=SC2016 # GraphQL variables must reach GitHub literally.
viewer_can_update=$(gh api graphql \
  -f query='query($id: ID!) { node(id: $id) { ... on ProjectV2 { viewerCanUpdate } } }' \
  -F id="${project_id}" \
  --jq '.data.node.viewerCanUpdate')
[ "${viewer_can_update}" = "true" ] ||
  fail "The active GitHub account cannot update Project ${PROJECT_OWNER}/${PROJECT_NUMBER}"

if [ -z "${start_field_id}" ]; then
  start_field_id=$(gh project field-create "${PROJECT_NUMBER}" \
    --owner "${PROJECT_OWNER}" \
    --name "${START_FIELD_NAME}" \
    --data-type DATE \
    --format json \
    --jq '.id')
  log "CREATED FIELD ${START_FIELD_NAME}"
fi

if [ -z "${responsibles_field_id}" ]; then
  responsibles_field_id=$(gh project field-create "${PROJECT_NUMBER}" \
    --owner "${PROJECT_OWNER}" \
    --name "${RESPONSIBLES_FIELD_NAME}" \
    --data-type TEXT \
    --format json \
    --jq '.id')
  log "CREATED FIELD ${RESPONSIBLES_FIELD_NAME}"
fi

while IFS="${TAB}" read -r week start end title responsibles body item_id; do
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
    --field-id "${responsibles_field_id}" \
    --text "${responsibles}" >/dev/null

  gh project item-edit \
    --id "${item_id}" \
    --project-id "${project_id}" \
    --field-id "${status_field_id}" \
    --single-select-option-id "${done_option_id}" >/dev/null

  log "${action} ${week} ${start} -> ${end} [Done]"
done <"${RESOLVED_WEEKS_TSV}"

log "Complete. S1-S8 are available as completed dated Project items."
