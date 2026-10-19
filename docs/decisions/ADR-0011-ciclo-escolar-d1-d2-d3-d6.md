# ADR-0011: aporte D1, D2, D3 y D6, ciclo de vida del ciclo escolar

## Estado y alcance

Aceptada por `docs/ux-ui.md`, sección 3, e implementada en el backend en la entrega 1 del
issue #631 (rama `feat/631-ciclo-estructura`). Este archivo aporta D1, D2, D3 y D6 al
[ADR-0011](ADR-0011-decisiones-ux-ui.md). La interfaz (botones, textos y lista de
verificación) llega en la parte de frontend de la misma entrega; hasta entonces los
requerimientos afectados quedan «En progreso» en el catálogo.

## Contexto

El ciclo escolar es la raíz de secciones, matrícula, asignaciones, evaluación y asistencia, y su
ciclo de vida no se podía completar desde la interfaz:

- «Clonar» solo aceptaba ciclos cerrados, así que no servía para preparar el siguiente ciclo
  mientras el actual seguía en curso (C2).
- No había forma de deshacer una activación hecha por error (C10).
- Cuando activar fallaba, el backend devolvía un único párrafo con todos los faltantes (C7), y
  la interfaz no podía explicar por adelantado por qué un botón no aplica (C5, D1).

## Decisión

### D1. Para activar hay que cerrar antes el ciclo activo

El backend ya lo exigía y no cambia. Para que la interfaz lo explique sin intentar la
acción, `GET /academics/cycles/{id}/readiness/` devuelve `active_cycle` (el otro ciclo activo
de la institución, con `public_id` y nombre) y, en la lista de activación, el faltante
`active_cycle_exists`.

### D2. Se puede clonar un ciclo activo

`clone_academic_cycle` acepta ciclos `ACTIVE` y `CLOSED` y rechaza los borradores con
«No se puede clonar un ciclo en borrador; active o cierre el ciclo antes de clonarlo.». Un
borrador todavía se está escribiendo; copiarlo duplicaría una estructura a medias. Con origen
activo o cerrado se copian solo las asignaciones vigentes (`ends_on` nulo). Clonar corre ahora
en una sola transacción: una falla a mitad del clonado no deja filas parciales.

### D3. Existe «volver a borrador»

`revert_academic_cycle_to_draft(academic_cycle, reason, actor)` devuelve un ciclo `ACTIVE` a
`DRAFT`. Bloquea el ciclo (`select_for_update`), exige motivo y deja el evento
`academics.cycle.reverted_to_draft` con el motivo y el estado anterior. Conserva la estructura
(ofertas, secciones y planes) y las asignaciones docentes: el propósito es corregir y volver a
activar, no empezar de cero. Endpoint: `POST /academics/cycles/{id}/revert-to-draft/` con
`{reason}`.

### D6. Volver a borrador solo antes de que haya actividad

Se permite únicamente si el ciclo no tiene ninguna de estas actividades. Cada bloqueo se informa
con un código, una cantidad y un mensaje («Tiene 312 matrículas.»):

| Código | Actividad | Cómo se cuenta |
| --- | --- | --- |
| `enrolments` | Matrículas de cualquier estado | `cycle.enrolments` |
| `grades` | Notas de unidad y de recuperación | `enrolments` → `grades` y `recovery_grades` |
| `attendance_events` | Movimientos de asistencia | Jornadas de la institución → `attendance_events` con `event_date` dentro de la vigencia del ciclo |
| `closed_evaluation_units` | Unidades de evaluación cerradas | `cycle.evaluation_units` con estado `closed` |
| `issued_documents` | Documentos emitidos | `enrolments` → `document_issuances` |

Una unidad de evaluación abierta no bloquea: todavía no produjo nada que deshacer. Con
actividad, la vía es cerrar el ciclo y, si hace falta, reabrirlo (RF-CIC-005), que conserva la
traza completa.

El permiso es `academic_cycle.revert` (código `academic_cycle_revert`, ya sembrado por
`identity/0014`). La vista lo exige con alcance sobre la institución mediante
`CatalogueView.require_revert_scope`, igual que `require_reopen_scope`: sin la llave
`academic_cycle` en el alcance, porque `scope_matches` negaría un ciclo por su estado antes de
evaluar el permiso. Ni `scope.assign` ni `academic_cycle.reopen` lo sustituyen.

## Cómo se detecta la actividad sin romper las capas

`academics` está por debajo de matrícula, evaluación, asistencia y documentos
([domain-map.md](../architecture/domain-map.md)). `academic_cycle_revert_blockers` no importa
ningún módulo de esos dominios: recorre **relaciones inversas por nombre** (`enrolments`,
`grades`, `recovery_grades`, `evaluation_units`, `attendance_events`, `document_issuances`) desde
modelos propios (`AcademicCycle` y `Shift`). Es el mismo mecanismo que ya usaban
`_cycle_closure_gaps` (ahora `queries.academic_cycle_closure_gaps`) y
`Section.active_enrolment_count`.

Se descartaron dos alternativas:

- `apps.get_model(...)`: oculta la dependencia en una cadena y no aporta nada frente a la
  relación inversa, que Django ya resuelve con el mismo acoplamiento por nombre.
- Un registro de «proveedores de actividad» donde cada dominio se inscribe: más flexible, pero
  es infraestructura nueva para cinco conteos fijos que D6 enumera explícitamente. Si aparece una
  sexta actividad de un dominio nuevo, se reconsidera.

Asistencia no tiene llave al ciclo: un evento pertenece al ciclo de la institución de su jornada
cuyo rango cubre `event_date`, igual que `attendance.services.resolve_academic_cycle_for`. Los
ciclos de una institución no se traslapan (`academic_cycle_no_overlapping_dates`), así que la
asignación es exacta.

## Lista de verificación (C7)

`_academic_cycle_opening_gaps` pasó a `queries.academic_cycle_opening_gaps` y devuelve faltantes
estructurados `{code, message, grade, section, subject}` (`no_grade_offerings`,
`missing_sections`, `missing_curriculum_plan`, `missing_teacher`). `activate_academic_cycle`
une los mensajes y conserva el texto de error equivalente. Los faltantes del cierre
(`evaluation_unit_open`, `recovery_window_open`) siguen el mismo patrón. Todos los mensajes
quedan en español con tildes (RNF-LOC-002).

## Consecuencias

- Un ciclo activado por error se corrige sin perder estructura ni asignaciones, y sin borrar
  historia: el regreso queda auditado con su motivo.
- La interfaz puede deshabilitar Activar, Volver a borrador y Cerrar con la explicación exacta
  sin intentar la acción.
- El conteo de actividad lee tablas de otros dominios por relación inversa. Renombrar uno de
  esos `related_name` rompe `academic_cycle_revert_blockers`; las pruebas
  `test_revert_is_blocked_by_each_kind_of_activity` cubren cada uno.
- Concurrencia: el conteo corre con el ciclo bloqueado, pero las altas de matrícula o asistencia
  no bloquean el ciclo. Una matrícula registrada en el mismo instante podría quedar en un ciclo
  recién devuelto a borrador; el borrador no la borra y la siguiente activación la conserva.
  Se acepta el riesgo por lo improbable de la coincidencia y porque no se pierde información.

## Requerimientos y evidencia

- RF-CIC-007 (D2): `tests/unit/test_academics_services.py`
  (`test_clone_cycle_from_active_source_copies_only_current_assignments`,
  `test_clone_cycle_rejects_draft_source_with_clear_message`,
  `test_clone_cycle_is_atomic_and_leaves_no_partial_rows_on_failure`).
- RF-CIC-008 (D3, D6): `tests/unit/test_academic_cycle_lifecycle_services.py`,
  `tests/api/test_academic_cycle_lifecycle_api.py` y
  `tests/permissions/test_academic_cycle_permissions.py`.
- RF-CIC-003 (C7, D1): las mismas pruebas de preparación y las de activación existentes.
