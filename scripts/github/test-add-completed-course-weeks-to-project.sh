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

field_value() {
  field=$1
  shift
  while [ "$#" -gt 0 ]; do
    case "$1" in
      "${field}="*) printf '%s\n' "${1#*=}"; return ;;
    esac
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
        printf '%s\n' '{"totalCount":3,"fields":[{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"responsibles-id","name":"Responsables","type":"ProjectV2Field"},{"id":"status-id","name":"Status","type":"ProjectV2SingleSelectField","options":[{"id":"done-id","name":"Done"}]}]}'
        ;;
      missing-responsibles)
        printf '%s\n' '{"totalCount":3,"fields":[{"id":"start-id","name":"Fecha inicio","type":"ProjectV2Field"},{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"status-id","name":"Status","type":"ProjectV2SingleSelectField","options":[{"id":"done-id","name":"Done"}]}]}'
        ;;
      fields-truncated)
        printf '%s\n' '{"totalCount":5,"fields":[{"id":"start-id","name":"Fecha inicio","type":"ProjectV2Field"},{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"responsibles-id","name":"Responsables","type":"ProjectV2Field"},{"id":"status-id","name":"Status","type":"ProjectV2SingleSelectField","options":[{"id":"done-id","name":"Done"}]}]}'
        ;;
      duplicate-fields)
        printf '%s\n' '{"totalCount":5,"fields":[{"id":"start-id","name":"Fecha inicio","type":"ProjectV2Field"},{"id":"duplicate-start-id","name":"Fecha inicio","type":"ProjectV2Field"},{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"responsibles-id","name":"Responsables","type":"ProjectV2Field"},{"id":"status-id","name":"Status","type":"ProjectV2SingleSelectField","options":[{"id":"done-id","name":"Done"}]}]}'
        ;;
      missing-status)
        printf '%s\n' '{"totalCount":3,"fields":[{"id":"start-id","name":"Fecha inicio","type":"ProjectV2Field"},{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"responsibles-id","name":"Responsables","type":"ProjectV2Field"}]}'
        ;;
      duplicate-status)
        printf '%s\n' '{"totalCount":5,"fields":[{"id":"start-id","name":"Fecha inicio","type":"ProjectV2Field"},{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"responsibles-id","name":"Responsables","type":"ProjectV2Field"},{"id":"status-id","name":"Status","type":"ProjectV2SingleSelectField","options":[{"id":"done-id","name":"Done"}]},{"id":"duplicate-status-id","name":"Status","type":"ProjectV2SingleSelectField","options":[{"id":"other-id","name":"Other"}]}]}'
        ;;
      wrong-status-type)
        printf '%s\n' '{"totalCount":4,"fields":[{"id":"start-id","name":"Fecha inicio","type":"ProjectV2Field"},{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"responsibles-id","name":"Responsables","type":"ProjectV2Field"},{"id":"status-id","name":"Status","type":"ProjectV2Field"}]}'
        ;;
      missing-done-option)
        printf '%s\n' '{"totalCount":4,"fields":[{"id":"start-id","name":"Fecha inicio","type":"ProjectV2Field"},{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"responsibles-id","name":"Responsables","type":"ProjectV2Field"},{"id":"status-id","name":"Status","type":"ProjectV2SingleSelectField","options":[{"id":"other-id","name":"Other"}]}]}'
        ;;
      duplicate-done-options)
        printf '%s\n' '{"totalCount":4,"fields":[{"id":"start-id","name":"Fecha inicio","type":"ProjectV2Field"},{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"responsibles-id","name":"Responsables","type":"ProjectV2Field"},{"id":"status-id","name":"Status","type":"ProjectV2SingleSelectField","options":[{"id":"done-id","name":"Done"},{"id":"duplicate-done-id","name":"Done"}]}]}'
        ;;
      *)
        printf '%s\n' '{"totalCount":4,"fields":[{"id":"start-id","name":"Fecha inicio","type":"ProjectV2Field"},{"id":"end-id","name":"Fecha esperada","type":"ProjectV2Field"},{"id":"responsibles-id","name":"Responsables","type":"ProjectV2Field"},{"id":"status-id","name":"Status","type":"ProjectV2SingleSelectField","options":[{"id":"done-id","name":"Done"}]}]}'
        ;;
    esac
    ;;
  "project item-list 1 --owner test --limit 1000 --format json")
    case "${GH_SCENARIO:-one}" in
      all)
        printf '%s\n' '{"totalCount":8,"items":[{"id":"existing-s1","title":"S1 · Inicio y organización del proyecto","body":"old <!-- siga-inebi:course-week:S1 -->","content":{"type":"DraftIssue"}},{"id":"existing-s2","title":"S2 · Institución, problema y formalización","body":"old <!-- siga-inebi:course-week:S2 -->","content":{"type":"DraftIssue"}},{"id":"existing-s3","title":"S3 · Levantamiento y proceso actual","body":"old <!-- siga-inebi:course-week:S3 -->","content":{"type":"DraftIssue"}},{"id":"existing-s4","title":"S4 · Requerimientos y alcance","body":"old <!-- siga-inebi:course-week:S4 -->","content":{"type":"DraftIssue"}},{"id":"existing-s5","title":"S5 · Priorización, trazabilidad y validación","body":"old <!-- siga-inebi:course-week:S5 -->","content":{"type":"DraftIssue"}},{"id":"existing-s6","title":"S6 · Modelado UML del sistema","body":"old <!-- siga-inebi:course-week:S6 -->","content":{"type":"DraftIssue"}},{"id":"existing-s7","title":"S7 · Arquitectura y diseño lógico de datos","body":"old <!-- siga-inebi:course-week:S7 -->","content":{"type":"DraftIssue"}},{"id":"existing-s8","title":"S8 · Diseño físico, interfaces y validación","body":"old <!-- siga-inebi:course-week:S8 -->","content":{"type":"DraftIssue"}}]}'
        ;;
      duplicate)
        printf '%s\n' '{"totalCount":2,"items":[{"id":"duplicate-s8-a","title":"S8 · Diseño físico, interfaces y validación","content":{"type":"DraftIssue"}},{"id":"duplicate-s8-b","title":"S8 · Diseño físico, interfaces y validación","content":{"type":"DraftIssue"}}]}'
        ;;
      truncated)
        printf '%s\n' '{"totalCount":2,"items":[{"id":"existing-s1","title":"S1 · Inicio y organización del proyecto","body":"old <!-- siga-inebi:course-week:S1 -->","content":{"type":"DraftIssue"}}]}'
        ;;
      unowned)
        printf '%s\n' '{"totalCount":1,"items":[{"id":"existing-s1","title":"S1 · Inicio y organización del proyecto","body":"Unrelated draft","content":{"type":"DraftIssue"}}]}'
        ;;
      *)
        printf '%s\n' '{"totalCount":2,"items":[{"id":"repository-s1","title":"S1 · Inicio y organización del proyecto","content":{"type":"Issue"}},{"id":"existing-s1","title":"S1 · Inicio y organización del proyecto","body":"old <!-- siga-inebi:course-week:S1 -->","content":{"type":"DraftIssue"}}]}'
        ;;
    esac
    ;;
  api\ graphql*)
    node_id=$(field_value id "$@")
    printf '%s\n' "api graphql ${node_id}" >>"${GH_QUERIES}"
    case "${node_id}" in
      project-id)
        if [ "${GH_SCENARIO:-one}" = "permission-denied" ]; then
          printf '%s\n' 'false'
        else
          printf '%s\n' 'true'
        fi
        ;;
      start-id|duplicate-start-id|end-id) printf '%s\n' 'DATE' ;;
      responsibles-id)
        if [ "${GH_SCENARIO:-one}" = "wrong-responsibles-type" ]; then
          printf '%s\n' 'NUMBER'
        else
          printf '%s\n' 'TEXT'
        fi
        ;;
      *) printf 'Unexpected GraphQL node id: %s\n' "${node_id}" >&2; exit 1 ;;
    esac
    ;;
  "project field-create 1 --owner test --name Fecha inicio --data-type DATE --format json --jq .id")
    printf '%s\n' "$*" >>"${GH_WRITES}"
    printf '%s\n' 'created-start-id'
    ;;
  "project field-create 1 --owner test --name Responsables --data-type TEXT --format json --jq .id")
    printf '%s\n' "$*" >>"${GH_WRITES}"
    printf '%s\n' 'created-responsibles-id'
    ;;
  project\ item-create\ 1\ --owner\ test*)
    title=$(argument_value --title "$@")
    body=$(argument_value --body "$@")
    printf '%s\n' "$*" >>"${GH_WRITES}"
    case "${title}" in
      "S2 · Institución, problema y formalización") expected_body="Resumen oficial de S2: selección de la institución, planteamiento preliminar del problema, factibilidad, acta de constitución, cronograma preliminar, comunicación y aprobación para continuar. No se suministró una asignación histórica individual."; week=S2; item_id=new-s2 ;;
      "S3 · Levantamiento y proceso actual") expected_body="Resumen oficial de S3: recopilación de información mediante entrevistas, observaciones y documentos; identificación de interesados; proceso actual AS-IS y necesidades identificadas. Evidencia histórica: visita técnica y levantamiento de requisitos e información. Pablo: plan y guía de entrevista, minuta, observaciones y documentos. Diana: mapa de interesados. Roí: proceso actual AS-IS y propuesta de proceso mejorado. La participación registrada en la visita corresponde a Pablo, Luis y Daniel; Diana conservó la responsabilidad del mapa de interesados."; week=S3; item_id=new-s3 ;;
      "S4 · Requerimientos y alcance") expected_body="Resumen oficial de S4: requisitos funcionales y no funcionales, reglas de negocio, alcance, exclusiones, restricciones, supuestos, historias de usuario y criterios de aceptación. Daniel: requisitos funcionales y no funcionales. Ángel: reglas de negocio, alcance, exclusiones, restricciones y supuestos. Luis: historias de usuario y criterios de aceptación. Estuardo: problema definitivo y objetivos general y específicos. Pablo: integración y revisión del documento."; week=S4; item_id=new-s4 ;;
      "S5 · Priorización, trazabilidad y validación") expected_body="Resumen oficial de S5: funciones priorizadas, matriz inicial de trazabilidad, análisis consolidado y validación institucional. Emilio: lista priorizada de funcionalidades. Josué: validación de requisitos con la institución. Trabajo conjunto: primera versión funcional y matriz inicial de trazabilidad. Daniel: coordinación técnica. Pablo: revisión de alineación. La matriz recibió apoyo de Daniel, Luis, Emilio y Santiago. Luis también imprimió y llevó los requisitos para su validación institucional."; week=S5; item_id=new-s5 ;;
      "S6 · Modelado UML del sistema") expected_body="Resumen oficial de S6: casos de uso, actividades y secuencias UML. No se suministró una asignación histórica individual."; week=S6; item_id=new-s6 ;;
      "S7 · Arquitectura y diseño lógico de datos") expected_body="Resumen oficial de S7: arquitectura, tecnologías, modelo conceptual y lógico de datos y diccionario preliminar. No se suministró una asignación histórica individual."; week=S7; item_id=new-s7 ;;
      "S8 · Diseño físico, interfaces y validación") expected_body="Resumen oficial de S8: modelo físico de datos, scripts iniciales, interfaces y prototipos, y validación del diseño. No se suministró una asignación histórica individual."; week=S8; item_id=new-s8 ;;
      *) printf 'Unexpected item title argument: %s\n' "${title}" >&2; exit 1 ;;
    esac
    expected_body="${expected_body} <!-- siga-inebi:course-week:${week} -->"
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
          existing-s1) expected_body="Resumen oficial de S1: organización del curso y del equipo, posible búsqueda de institución, configuración de Jira/GitHub y apertura del expediente digital del proyecto. No se suministró una asignación histórica individual."; week=S1 ;;
          existing-s2) expected_body="Resumen oficial de S2: selección de la institución, planteamiento preliminar del problema, factibilidad, acta de constitución, cronograma preliminar, comunicación y aprobación para continuar. No se suministró una asignación histórica individual."; week=S2 ;;
          existing-s3) expected_body="Resumen oficial de S3: recopilación de información mediante entrevistas, observaciones y documentos; identificación de interesados; proceso actual AS-IS y necesidades identificadas. Evidencia histórica: visita técnica y levantamiento de requisitos e información. Pablo: plan y guía de entrevista, minuta, observaciones y documentos. Diana: mapa de interesados. Roí: proceso actual AS-IS y propuesta de proceso mejorado. La participación registrada en la visita corresponde a Pablo, Luis y Daniel; Diana conservó la responsabilidad del mapa de interesados."; week=S3 ;;
          existing-s4) expected_body="Resumen oficial de S4: requisitos funcionales y no funcionales, reglas de negocio, alcance, exclusiones, restricciones, supuestos, historias de usuario y criterios de aceptación. Daniel: requisitos funcionales y no funcionales. Ángel: reglas de negocio, alcance, exclusiones, restricciones y supuestos. Luis: historias de usuario y criterios de aceptación. Estuardo: problema definitivo y objetivos general y específicos. Pablo: integración y revisión del documento."; week=S4 ;;
          existing-s5) expected_body="Resumen oficial de S5: funciones priorizadas, matriz inicial de trazabilidad, análisis consolidado y validación institucional. Emilio: lista priorizada de funcionalidades. Josué: validación de requisitos con la institución. Trabajo conjunto: primera versión funcional y matriz inicial de trazabilidad. Daniel: coordinación técnica. Pablo: revisión de alineación. La matriz recibió apoyo de Daniel, Luis, Emilio y Santiago. Luis también imprimió y llevó los requisitos para su validación institucional."; week=S5 ;;
          existing-s6) expected_body="Resumen oficial de S6: casos de uso, actividades y secuencias UML. No se suministró una asignación histórica individual."; week=S6 ;;
          existing-s7) expected_body="Resumen oficial de S7: arquitectura, tecnologías, modelo conceptual y lógico de datos y diccionario preliminar. No se suministró una asignación histórica individual."; week=S7 ;;
          existing-s8) expected_body="Resumen oficial de S8: modelo físico de datos, scripts iniciales, interfaces y prototipos, y validación del diseño. No se suministró una asignación histórica individual."; week=S8 ;;
          *) printf 'Unexpected body edit id: %s\n' "${item_id}" >&2; exit 1 ;;
        esac
        expected_body="${expected_body} <!-- siga-inebi:course-week:${week} -->"
        [ "${body}" = "${expected_body}" ] || {
          printf 'Unexpected body argument for %s: %s\n' "${item_id}" "${body}" >&2
          exit 1
        }
        ;;
      *" --text "*)
        item_id=$(argument_value --id "$@")
        text=$(argument_value --text "$@")
        case "${item_id}" in
          existing-s1|new-s2|existing-s2) expected_text="Equipo SIGA-INEBI" ;;
          new-s3|existing-s3) expected_text="Pablo (Crono); Luis Ovalle; Daniel Bautista; Diana; Roí" ;;
          new-s4|existing-s4) expected_text="Daniel; Ángel; Luis; Estuardo; Pablo (coordinación)" ;;
          new-s5|existing-s5) expected_text="Emilio; Josué; Daniel (coordinación técnica); Pablo (revisión); Luis; Santiago; equipo SIGA-INEBI" ;;
          new-s6|existing-s6|new-s7|existing-s7|new-s8|existing-s8) expected_text="Equipo SIGA-INEBI" ;;
          *) printf 'Unexpected responsibilities edit id: %s\n' "${item_id}" >&2; exit 1 ;;
        esac
        [ "${text}" = "${expected_text}" ] || {
          printf 'Unexpected responsibilities text for %s: %s\n' "${item_id}" "${text}" >&2
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
export GH_QUERIES="${WORK_DIR}/queries"

WEEK_COUNT=8
CREATED_WEEK_COUNT=7
FIELD_EDITS_PER_WEEK=4
BODY_EDITS_FOR_EXISTING_WEEKS=1
FIRST_APPLY_EDIT_COUNT=$((WEEK_COUNT * FIELD_EDITS_PER_WEEK + BODY_EDITS_FOR_EXISTING_WEEKS))
IDEMPOTENT_APPLY_EDIT_COUNT=$((WEEK_COUNT * (FIELD_EDITS_PER_WEEK + 1)))

# The supplied "Fase 2" evidence is distributed across S3-S5. Development
# allocations begin at S9 and are intentionally excluded from S1-S8.
if grep -E 'Identity|People|Academic|ciclos escolares|shell React|entrega académica pendiente' \
  "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >/dev/null; then
  printf '%s\n' "Unexpected later-stage development allocation in S1-S8" >&2
  exit 1
fi
if grep -F 'llegó tarde y no tuvo participación efectiva' \
  "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >/dev/null; then
  printf '%s\n' "Unexpected permanent reputation claim in S3" >&2
  exit 1
fi

dry_run=$(sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh")
printf '%s\n' "${dry_run}" | grep -F "UPDATE S1 2026-06-18 -> 2026-06-25 [Done]" >/dev/null
printf '%s\n' "${dry_run}" | grep -F "CREATE S8 2026-08-06 -> 2026-08-13 [Done]" >/dev/null
grep -F "api graphql start-id" "${GH_QUERIES}" >/dev/null
grep -F "api graphql end-id" "${GH_QUERIES}" >/dev/null
grep -F "api graphql responsibles-id" "${GH_QUERIES}" >/dev/null
[ "$(grep -c 'api graphql project-id' "${GH_QUERIES}" || true)" -eq 0 ]
[ ! -e "${GH_WRITES}" ]

rm -f "${GH_QUERIES}"
APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >/dev/null
grep -F "api graphql project-id" "${GH_QUERIES}" >/dev/null
[ "$(grep -c '^project item-create' "${GH_WRITES}")" -eq "${CREATED_WEEK_COUNT}" ]
[ "$(grep -c '^project item-edit' "${GH_WRITES}")" -eq "${FIRST_APPLY_EDIT_COUNT}" ]
grep -F -- "--id existing-s1 --body Resumen oficial de S1: organización del curso y del equipo, posible búsqueda de institución, configuración de Jira/GitHub y apertura del expediente digital del proyecto. No se suministró una asignación histórica individual. <!-- siga-inebi:course-week:S1 -->" "${GH_WRITES}" >/dev/null

assert_create_args() {
  title=$1
  week=$2
  body=$3
  body="${body} <!-- siga-inebi:course-week:${week} -->"
  grep -F -- "--title ${title} --body ${body} --format json --jq .id" "${GH_WRITES}" >/dev/null
}

assert_create_args "S2 · Institución, problema y formalización" S2 "Resumen oficial de S2: selección de la institución, planteamiento preliminar del problema, factibilidad, acta de constitución, cronograma preliminar, comunicación y aprobación para continuar. No se suministró una asignación histórica individual."
assert_create_args "S3 · Levantamiento y proceso actual" S3 "Resumen oficial de S3: recopilación de información mediante entrevistas, observaciones y documentos; identificación de interesados; proceso actual AS-IS y necesidades identificadas. Evidencia histórica: visita técnica y levantamiento de requisitos e información. Pablo: plan y guía de entrevista, minuta, observaciones y documentos. Diana: mapa de interesados. Roí: proceso actual AS-IS y propuesta de proceso mejorado. La participación registrada en la visita corresponde a Pablo, Luis y Daniel; Diana conservó la responsabilidad del mapa de interesados."
assert_create_args "S4 · Requerimientos y alcance" S4 "Resumen oficial de S4: requisitos funcionales y no funcionales, reglas de negocio, alcance, exclusiones, restricciones, supuestos, historias de usuario y criterios de aceptación. Daniel: requisitos funcionales y no funcionales. Ángel: reglas de negocio, alcance, exclusiones, restricciones y supuestos. Luis: historias de usuario y criterios de aceptación. Estuardo: problema definitivo y objetivos general y específicos. Pablo: integración y revisión del documento."
assert_create_args "S5 · Priorización, trazabilidad y validación" S5 "Resumen oficial de S5: funciones priorizadas, matriz inicial de trazabilidad, análisis consolidado y validación institucional. Emilio: lista priorizada de funcionalidades. Josué: validación de requisitos con la institución. Trabajo conjunto: primera versión funcional y matriz inicial de trazabilidad. Daniel: coordinación técnica. Pablo: revisión de alineación. La matriz recibió apoyo de Daniel, Luis, Emilio y Santiago. Luis también imprimió y llevó los requisitos para su validación institucional."
assert_create_args "S6 · Modelado UML del sistema" S6 "Resumen oficial de S6: casos de uso, actividades y secuencias UML. No se suministró una asignación histórica individual."
assert_create_args "S7 · Arquitectura y diseño lógico de datos" S7 "Resumen oficial de S7: arquitectura, tecnologías, modelo conceptual y lógico de datos y diccionario preliminar. No se suministró una asignación histórica individual."
assert_create_args "S8 · Diseño físico, interfaces y validación" S8 "Resumen oficial de S8: modelo físico de datos, scripts iniciales, interfaces y prototipos, y validación del diseño. No se suministró una asignación histórica individual."

assert_week_fields() {
  item_id=$1
  start=$2
  end=$3
  responsibles=$4
  if [ -n "${previous_end}" ]; then
    [ "${start}" = "${previous_end}" ]
  fi
  grep -F -- "--id ${item_id} --project-id project-id --field-id start-id --date ${start}" "${GH_WRITES}" >/dev/null
  grep -F -- "--id ${item_id} --project-id project-id --field-id end-id --date ${end}" "${GH_WRITES}" >/dev/null
  grep -F -- "--id ${item_id} --project-id project-id --field-id responsibles-id --text ${responsibles}" "${GH_WRITES}" >/dev/null
  grep -F -- "--id ${item_id} --project-id project-id --field-id status-id --single-select-option-id done-id" "${GH_WRITES}" >/dev/null
  previous_end=${end}
}

previous_end=
assert_week_fields existing-s1 2026-06-18 2026-06-25 "Equipo SIGA-INEBI"
assert_week_fields new-s2 2026-06-25 2026-07-02 "Equipo SIGA-INEBI"
assert_week_fields new-s3 2026-07-02 2026-07-09 "Pablo (Crono); Luis Ovalle; Daniel Bautista; Diana; Roí"
assert_week_fields new-s4 2026-07-09 2026-07-16 "Daniel; Ángel; Luis; Estuardo; Pablo (coordinación)"
assert_week_fields new-s5 2026-07-16 2026-07-23 "Emilio; Josué; Daniel (coordinación técnica); Pablo (revisión); Luis; Santiago; equipo SIGA-INEBI"
assert_week_fields new-s6 2026-07-23 2026-07-30 "Equipo SIGA-INEBI"
assert_week_fields new-s7 2026-07-30 2026-08-06 "Equipo SIGA-INEBI"
assert_week_fields new-s8 2026-08-06 2026-08-13 "Equipo SIGA-INEBI"

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
missing_responsibles_dry_run=$(GH_SCENARIO=missing-responsibles sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh")
printf '%s\n' "${missing_responsibles_dry_run}" | grep -F "CREATE FIELD Responsables (TEXT)" >/dev/null
[ ! -e "${GH_WRITES}" ]

GH_SCENARIO=missing-responsibles APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >/dev/null
[ "$(grep -c '^project field-create' "${GH_WRITES}")" -eq 1 ]
grep -F -- "--name Responsables --data-type TEXT" "${GH_WRITES}" >/dev/null
grep -F -- "--field-id created-responsibles-id --text Equipo SIGA-INEBI" "${GH_WRITES}" >/dev/null

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

if GH_SCENARIO=unowned APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >"${WORK_DIR}/unowned.out" 2>&1; then
  printf '%s\n' "Expected unowned exact-title draft to fail" >&2
  exit 1
fi
grep -F "Project draft item is not managed by this script" "${WORK_DIR}/unowned.out" >/dev/null
[ ! -e "${GH_WRITES}" ]

if GH_SCENARIO=duplicate-fields APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >"${WORK_DIR}/duplicate-fields.out" 2>&1; then
  printf '%s\n' "Expected duplicate field names to fail" >&2
  exit 1
fi
grep -F "Multiple Project fields have name: Fecha inicio" "${WORK_DIR}/duplicate-fields.out" >/dev/null
[ ! -e "${GH_WRITES}" ]

if GH_SCENARIO=missing-status APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >"${WORK_DIR}/missing-status.out" 2>&1; then
  printf '%s\n' "Expected missing Status field to fail" >&2
  exit 1
fi
grep -F "Missing Project field: Status" "${WORK_DIR}/missing-status.out" >/dev/null
[ ! -e "${GH_WRITES}" ]

if GH_SCENARIO=duplicate-status APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >"${WORK_DIR}/duplicate-status.out" 2>&1; then
  printf '%s\n' "Expected duplicate Status fields to fail" >&2
  exit 1
fi
grep -F "Multiple Project fields have name: Status" "${WORK_DIR}/duplicate-status.out" >/dev/null
[ ! -e "${GH_WRITES}" ]

if GH_SCENARIO=wrong-status-type APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >"${WORK_DIR}/wrong-status-type.out" 2>&1; then
  printf '%s\n' "Expected wrong Status type to fail" >&2
  exit 1
fi
grep -F "Project field Status must have type ProjectV2SingleSelectField; found ProjectV2Field" "${WORK_DIR}/wrong-status-type.out" >/dev/null
[ ! -e "${GH_WRITES}" ]

if GH_SCENARIO=missing-done-option APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >"${WORK_DIR}/missing-done-option.out" 2>&1; then
  printf '%s\n' "Expected missing Done option to fail" >&2
  exit 1
fi
grep -F "Missing Status option: Done" "${WORK_DIR}/missing-done-option.out" >/dev/null
[ ! -e "${GH_WRITES}" ]

if GH_SCENARIO=duplicate-done-options APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >"${WORK_DIR}/duplicate-done-options.out" 2>&1; then
  printf '%s\n' "Expected duplicate Done options to fail" >&2
  exit 1
fi
grep -F "Multiple Status options have name: Done" "${WORK_DIR}/duplicate-done-options.out" >/dev/null
[ ! -e "${GH_WRITES}" ]

if GH_SCENARIO=wrong-responsibles-type APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >"${WORK_DIR}/wrong-responsibles-type.out" 2>&1; then
  printf '%s\n' "Expected wrong Responsables type to fail" >&2
  exit 1
fi
grep -F "Project field Responsables must have data type TEXT; found NUMBER" "${WORK_DIR}/wrong-responsibles-type.out" >/dev/null
[ ! -e "${GH_WRITES}" ]

permission_dry_run=$(GH_SCENARIO=permission-denied sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh")
printf '%s\n' "${permission_dry_run}" | grep -F "Dry-run complete" >/dev/null
[ ! -e "${GH_WRITES}" ]

if GH_SCENARIO=permission-denied APPLY=true sh "${SCRIPT_DIR}/add-completed-course-weeks-to-project.sh" >"${WORK_DIR}/permission-denied.out" 2>&1; then
  printf '%s\n' "Expected missing Project write permission to fail" >&2
  exit 1
fi
grep -F "cannot update Project test/1" "${WORK_DIR}/permission-denied.out" >/dev/null
[ ! -e "${GH_WRITES}" ]

printf '%s\n' "PASS: add-completed-course-weeks-to-project.sh"
