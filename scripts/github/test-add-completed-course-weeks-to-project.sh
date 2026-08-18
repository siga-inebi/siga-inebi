#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
WORK_DIR=$(mktemp -d)
trap 'rm -rf "${WORK_DIR}"' EXIT

cat >"${WORK_DIR}/gh" <<'EOF'
#!/usr/bin/env sh
set -eu

argument_value() {
  option=$1
  shift
  while [ "$#" -gt 0 ]; do
    if [ "$1" = "${option}" ]; then
      [ "$#" -ge 2 ] || exit 1
      printf '%s\n' "$2"
      return
    fi
    shift
  done
  return 1
}

case "$*" in
  "auth status")
    exit 0
    ;;
  "project view 1 --owner test --format json --jq .id")
    printf '%s\n' 'project-id'
    ;;
  "project field-list 1 --owner test --limit 1000 --format json")
    case "${GH_SCENARIO:-one}" in
      missing-start)
        printf '%s\n' '{"totalCount":2,"fields":[{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"status-id","name":"Status","type":"ProjectV2SingleSelectField","options":[{"id":"done-id","name":"Done"}]}]}'
        ;;
      fields-truncated)
        printf '%s\n' '{"totalCount":4,"fields":[{"id":"start-id","name":"Fecha inicio","type":"ProjectV2Field"},{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"status-id","name":"Status","type":"ProjectV2SingleSelectField","options":[{"id":"done-id","name":"Done"}]}]}'
        ;;
      *)
        printf '%s\n' '{"totalCount":3,"fields":[{"id":"start-id","name":"Fecha inicio","type":"ProjectV2Field"},{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"status-id","name":"Status","type":"ProjectV2SingleSelectField","options":[{"id":"done-id","name":"Done"}]}]}'
        ;;
    esac
    ;;
  "project item-list 1 --owner test --limit 1000 --format json")
    case "${GH_SCENARIO:-one}" in
      all)
        printf '%s\n' '{"totalCount":8,"items":[{"id":"existing-s1","title":"S1 · Inicio y organización del proyecto","content":{"type":"DraftIssue"}},{"id":"existing-s2","title":"S2 · Institución, problema y formalización","content":{"type":"DraftIssue"}},{"id":"existing-s3","title":"S3 · Levantamiento y proceso actual","content":{"type":"DraftIssue"}},{"id":"existing-s4","title":"S4 · Requerimientos y alcance","content":{"type":"DraftIssue"}},{"id":"existing-s5","title":"S5 · Priorización, trazabilidad y validación","content":{"type":"DraftIssue"}},{"id":"existing-s6","title":"S6 · Modelado UML del sistema","content":{"type":"DraftIssue"}},{"id":"existing-s7","title":"S7 · Arquitectura y diseño lógico de datos","content":{"type":"DraftIssue"}},{"id":"existing-s8","title":"S8 · Diseño físico, interfaces y validación","content":{"type":"DraftIssue"}}]}'
        ;;
      duplicate)
        printf '%s\n' '{"totalCount":2,"items":[{"id":"duplicate-s8-a","title":"S8 · Diseño físico, interfaces y validación","content":{"type":"DraftIssue"}},{"id":"duplicate-s8-b","title":"S8 · Diseño físico, interfaces y validación","content":{"type":"DraftIssue"}}]}'
        ;;
      truncated)
        printf '%s\n' '{"totalCount":2,"items":[{"id":"existing-s1","title":"S1 · Inicio y organización del proyecto","content":{"type":"DraftIssue"}}]}'
        ;;
      *)
        printf '%s\n' '{"totalCount":2,"items":[{"id":"repository-s1","title":"S1 · Inicio y organización del proyecto","content":{"type":"Issue"}},{"id":"existing-s1","title":"S1 · Inicio y organización del proyecto","content":{"type":"DraftIssue"}}]}'
        ;;
    esac
    ;;
  "project field-create 1 --owner test --name Fecha inicio --data-type DATE --format json --jq .id")
    printf '%s\n' "$*" >>"${GH_WRITES}"
    printf '%s\n' 'created-start-id'
    ;;
  project\ item-create\ 1\ --owner\ test*)
    title=$(argument_value --title "$@")
    body=$(argument_value --body "$@")
    printf '%s\n' "$*" >>"${GH_WRITES}"
    case "${title}" in
      "S2 · Institución, problema y formalización") expected_body="Institución beneficiaria y problema identificados; factibilidad, acta de constitución, cronograma preliminar y plan de comunicación preparados."; item_id=new-s2 ;;
      "S3 · Levantamiento y proceso actual") expected_body="Entrevistas, observación, partes interesadas, proceso AS-IS y necesidades principales documentados."; item_id=new-s3 ;;
      "S4 · Requerimientos y alcance") expected_body="Requerimientos funcionales y no funcionales, reglas de negocio, alcance, historias de usuario y criterios de aceptación definidos."; item_id=new-s4 ;;
      "S5 · Priorización, trazabilidad y validación") expected_body="Funcionalidades priorizadas, matriz de trazabilidad creada y análisis validado con la institución."; item_id=new-s5 ;;
      "S6 · Modelado UML del sistema") expected_body="Casos de uso, actividades y secuencias modelados y contrastados con los requerimientos."; item_id=new-s6 ;;
      "S7 · Arquitectura y diseño lógico de datos") expected_body="Arquitectura, componentes, tecnologías, modelo conceptual, modelo lógico y diccionario preliminar definidos."; item_id=new-s7 ;;
      "S8 · Diseño físico, interfaces y validación") expected_body="Modelo físico, scripts iniciales, prototipos de interfaz y documento de diseño validados antes del desarrollo."; item_id=new-s8 ;;
      *) printf 'Unexpected item title argument: %s\n' "${title}" >&2; exit 1 ;;
    esac
    [ "${body}" = "${expected_body}" ] || {
      printf 'Unexpected body argument for %s: %s\n' "${title}" "${body}" >&2
      exit 1
    }
    printf '%s\n' "${item_id}"
    ;;
  project\ item-edit*)
    case " $* " in
      *" --body "*)
        item_id=$(argument_value --id "$@")
        body=$(argument_value --body "$@")
        case "${item_id}" in
          existing-s1) expected_body="Equipo conformado, herramientas colaborativas configuradas, repositorio organizado y expediente digital iniciado." ;;
          existing-s2) expected_body="Institución beneficiaria y problema identificados; factibilidad, acta de constitución, cronograma preliminar y plan de comunicación preparados." ;;
          existing-s3) expected_body="Entrevistas, observación, partes interesadas, proceso AS-IS y necesidades principales documentados." ;;
          existing-s4) expected_body="Requerimientos funcionales y no funcionales, reglas de negocio, alcance, historias de usuario y criterios de aceptación definidos." ;;
          existing-s5) expected_body="Funcionalidades priorizadas, matriz de trazabilidad creada y análisis validado con la institución." ;;
          existing-s6) expected_body="Casos de uso, actividades y secuencias modelados y contrastados con los requerimientos." ;;
          existing-s7) expected_body="Arquitectura, componentes, tecnologías, modelo conceptual, modelo lógico y diccionario preliminar definidos." ;;
          existing-s8) expected_body="Modelo físico, scripts iniciales, prototipos de interfaz y documento de diseño validados antes del desarrollo." ;;
          *) printf 'Unexpected body edit id: %s\n' "${item_id}" >&2; exit 1 ;;
        esac
        [ "${body}" = "${expected_body}" ] || {
          printf 'Unexpected body argument for %s: %s\n' "${item_id}" "${body}" >&2
          exit 1
        }
        ;;
    esac
    printf '%s\n' "$*" >>"${GH_WRITES}"
    ;;
  *)
    printf 'Unexpected gh call: %s\n' "$*" >&2
    exit 1
    ;;
esac
EOF
chmod +x "${WORK_DIR}/gh"

export PATH="${WORK_DIR}:${PATH}"
export PROJECT_OWNER="test"
export PROJECT_NUMBER="1"
export GH_WRITES="${WORK_DIR}/writes"

WEEK_COUNT=8
CREATED_WEEK_COUNT=7
FIELD_EDITS_PER_WEEK=3
BODY_EDITS_FOR_EXISTING_WEEKS=1
FIRST_APPLY_EDIT_COUNT=$((WEEK_COUNT * FIELD_EDITS_PER_WEEK + BODY_EDITS_FOR_EXISTING_WEEKS))
IDEMPOTENT_APPLY_EDIT_COUNT=$((WEEK_COUNT * (FIELD_EDITS_PER_WEEK + 1)))

dry_run=$(sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh")
printf '%s\n' "${dry_run}" | grep -F "UPDATE S1 2026-06-18 -> 2026-06-25 [Done]" >/dev/null
printf '%s\n' "${dry_run}" | grep -F "CREATE S8 2026-08-06 -> 2026-08-13 [Done]" >/dev/null
[ ! -e "${GH_WRITES}" ]

APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >/dev/null
[ "$(grep -c '^project item-create' "${GH_WRITES}")" -eq "${CREATED_WEEK_COUNT}" ]
[ "$(grep -c '^project item-edit' "${GH_WRITES}")" -eq "${FIRST_APPLY_EDIT_COUNT}" ]
grep -F -- "--id existing-s1 --body Equipo conformado, herramientas colaborativas configuradas, repositorio organizado y expediente digital iniciado." "${GH_WRITES}" >/dev/null

assert_create_args() {
  title=$1
  body=$2
  grep -F -- "--title ${title} --body ${body} --format json --jq .id" "${GH_WRITES}" >/dev/null
}

assert_create_args "S2 · Institución, problema y formalización" "Institución beneficiaria y problema identificados; factibilidad, acta de constitución, cronograma preliminar y plan de comunicación preparados."
assert_create_args "S3 · Levantamiento y proceso actual" "Entrevistas, observación, partes interesadas, proceso AS-IS y necesidades principales documentados."
assert_create_args "S4 · Requerimientos y alcance" "Requerimientos funcionales y no funcionales, reglas de negocio, alcance, historias de usuario y criterios de aceptación definidos."
assert_create_args "S5 · Priorización, trazabilidad y validación" "Funcionalidades priorizadas, matriz de trazabilidad creada y análisis validado con la institución."
assert_create_args "S6 · Modelado UML del sistema" "Casos de uso, actividades y secuencias modelados y contrastados con los requerimientos."
assert_create_args "S7 · Arquitectura y diseño lógico de datos" "Arquitectura, componentes, tecnologías, modelo conceptual, modelo lógico y diccionario preliminar definidos."
assert_create_args "S8 · Diseño físico, interfaces y validación" "Modelo físico, scripts iniciales, prototipos de interfaz y documento de diseño validados antes del desarrollo."

assert_week_fields() {
  item_id=$1
  start=$2
  end=$3
  if [ -n "${previous_end}" ]; then
    [ "${start}" = "${previous_end}" ]
  fi
  grep -F -- "--id ${item_id} --project-id project-id --field-id start-id --date ${start}" "${GH_WRITES}" >/dev/null
  grep -F -- "--id ${item_id} --project-id project-id --field-id end-id --date ${end}" "${GH_WRITES}" >/dev/null
  grep -F -- "--id ${item_id} --project-id project-id --field-id status-id --single-select-option-id done-id" "${GH_WRITES}" >/dev/null
  previous_end=${end}
}

previous_end=
assert_week_fields existing-s1 2026-06-18 2026-06-25
assert_week_fields new-s2 2026-06-25 2026-07-02
assert_week_fields new-s3 2026-07-02 2026-07-09
assert_week_fields new-s4 2026-07-09 2026-07-16
assert_week_fields new-s5 2026-07-16 2026-07-23
assert_week_fields new-s6 2026-07-23 2026-07-30
assert_week_fields new-s7 2026-07-30 2026-08-06
assert_week_fields new-s8 2026-08-06 2026-08-13

rm -f "${GH_WRITES}"
GH_SCENARIO=all APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >/dev/null
[ "$(grep -c '^project item-create' "${GH_WRITES}" 2>/dev/null || true)" -eq 0 ]
[ "$(grep -c '^project item-edit' "${GH_WRITES}")" -eq "${IDEMPOTENT_APPLY_EDIT_COUNT}" ]
[ "$(grep -c -- ' --body ' "${GH_WRITES}")" -eq "${WEEK_COUNT}" ]

rm -f "${GH_WRITES}"
GH_SCENARIO=missing-start APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >/dev/null
[ "$(grep -c '^project field-create' "${GH_WRITES}")" -eq 1 ]
grep -F -- "--field-id created-start-id --date 2026-06-18" "${GH_WRITES}" >/dev/null

rm -f "${GH_WRITES}"
if GH_SCENARIO=truncated APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >"${WORK_DIR}/truncated.out" 2>&1; then
  printf '%s\n' "Expected truncated item list to fail" >&2
  exit 1
fi
grep -F "Project item list was truncated" "${WORK_DIR}/truncated.out" >/dev/null
[ ! -e "${GH_WRITES}" ]

if GH_SCENARIO=fields-truncated APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >"${WORK_DIR}/fields-truncated.out" 2>&1; then
  printf '%s\n' "Expected truncated field list to fail" >&2
  exit 1
fi
grep -F "Project field list was truncated" "${WORK_DIR}/fields-truncated.out" >/dev/null
[ ! -e "${GH_WRITES}" ]

if GH_SCENARIO=duplicate APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >"${WORK_DIR}/duplicate.out" 2>&1; then
  printf '%s\n' "Expected duplicate draft titles to fail" >&2
  exit 1
fi
grep -F "Multiple Project draft items have title" "${WORK_DIR}/duplicate.out" >/dev/null
[ ! -e "${GH_WRITES}" ]

printf '%s\n' "PASS: add-completed-course-weeks-to-project.sh"
