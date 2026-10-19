# Permisos en la interfaz: acción → permiso atómico

Complemento de [ux-writing.md](ux-writing.md), sección 7, y de
[ADR-0011](../decisions/ADR-0011-decisiones-ux-ui.md). Regla de docs/ux-ui.md
1.4: **ningún botón visible sin su permiso**. La interfaz lo resuelve con
`<Can permission="…">` o `usePermissions().can(…)`
(`frontend/src/auth/Can.jsx`, `frontend/src/auth/usePermissions.js`) usando los
permisos efectivos de `/auth/me/`. Es presentación: el backend vuelve a
autorizar cada operación y niega por defecto.

La columna "Permiso que exige el backend" sale de leer la vista o el servicio
que atiende la petición (revisión del 2026-10-18 sobre `develop` +
`feat/ux-base-identidad-acceso`). "**Sin control de permiso**" significa que el
backend solo exige sesión: es un hueco a cerrar por el dueño del módulo en el
backend antes (o a la vez) que el botón. Esos huecos se siguen en el issue
[#643](https://github.com/siga-inebi/siga-inebi/issues/643) ("security: exigir permisos atómicos en los endpoints que solo piden
sesión").

Notación: `x.y` es el código público del permiso; "con alcance" indica que,
además del permiso, se evalúa el alcance sobre el recurso (estudiante,
institución, módulo).

## Comunidad educativa (Persona 3)

| Pantalla | Acción (botón) | Endpoint | Permiso que exige el backend |
| --- | --- | --- | --- |
| Estudiantes | Nuevo estudiante / Crear estudiante | `POST /students/` | `student.edit_basic` con alcance (módulo `students`) |
| Estudiantes | Editar / Guardar cambios | `PATCH /students/{id}/` | `student.edit_basic` con alcance sobre el estudiante |
| Estudiantes | Vincular encargado | `POST /students/guardian-relations/` | `student.edit_basic` con alcance |
| Estudiantes | Marcar principal / finalizar relación (aún sin UI) | `/guardian-relations/{id}/make-primary/`, `/end/` | `student.edit_basic` con alcance |
| Estudiantes | Salud → Registrar nota | `POST /students/{id}/health-notes/` | `student.view_sensitive` **y** `student.edit_basic`, con alcance |
| Estudiantes | Observaciones → Registrar observación | `POST /students/{id}/observations/` | `student.view_sensitive` **y** `student.edit_basic`, con alcance |
| Estudiantes | Contactos de emergencia → Registrar contacto | `POST /students/{id}/emergency-contacts/` | `student.view_sensitive` **y** `student.edit_basic`, con alcance |
| Estudiantes | Ver Salud / Observaciones / Contactos | `GET` de esos recursos | `student.view_sensitive` con alcance |
| Estudiantes | Exportar CSV | `GET /students/` (todas las páginas) | `student.view_basic` con alcance |
| Docentes | Nuevo docente / Crear registro | `POST /teachers/` | **Sin control de permiso** |
| Docentes | Editar / Guardar cambios | `PATCH /teachers/{id}/` | **Sin control de permiso** |
| Docentes | Documentos → Adjuntar documento | `POST /documents/teachers/{id}/records/` | `document.upload` con alcance (módulo `teachers`) |
| Docentes | Documentos → Descargar | `POST /documents/records/{id}/download-tokens/` | `document.read` con alcance (módulo `teachers`) |
| Docentes | Exportar CSV | `GET /teachers/` | **Sin control de permiso** |
| Docentes | Dar acceso al sistema | `POST /identity/accounts/` | `account.create` (módulo `identity`) — ya filtrado |
| Padres de familia | Nuevo encargado | `POST /students/guardians/` | **Sin control de permiso** |
| Padres de familia | Editar | `PATCH /students/guardians/{id}/` | **Sin control de permiso** |
| Padres de familia | Exportar CSV | `GET /students/guardians/` | **Sin control de permiso** |
| Personas | Nueva persona / Crear persona | `POST /people/` | **Sin control de permiso** (previsto `person.edit`, ADR-0011) |
| Personas | Editar | `PATCH /people/{id}/` | **Sin control de permiso** (previsto `person.edit`) |
| Personas | Desactivar | `DELETE /people/{id}/` | **Sin control de permiso** (previsto `person.edit`) |
| Personas | Ver listado | `GET /people/` | **Sin control de permiso** (previsto `person.view`) |
| Personas | Dar acceso al sistema | `POST /identity/accounts/` | `account.create` — ya filtrado |
| Matrículas | Matricular | `POST /enrolments/matriculations/` | `enrollment.create` |
| Matrículas | Reinscribir | `POST /enrolments/re-enrolments/` | `enrollment.create` |
| Matrículas | Matricular por lotes | `POST /enrolments/matriculations/` (una por estudiante) | `enrollment.create` |
| Matrículas | Movimientos (ver historial) | `GET /enrolments/movements/` | **Sin control de permiso** |
| Matrículas | Requisitos documentales → Agregar requisito | `POST /enrolments/{id}/documents/` | `enrollment.create`/`enrollment.update` vía `ensure_enrolment_permission` |
| Matrículas | Requisitos → Adjuntar archivo | `POST /documents/records/` | `document.upload` con alcance sobre el estudiante |
| Matrículas | Requisitos → Emitir constancia / certificado | `POST /documents/official-issuance/individual/` | `document.issue` |
| Plantillas | Nueva plantilla / Editar / Guardar versión / Desactivar | `/documents/templates/` | `scope.assign` con alcance sobre la institución |
| Plantillas | Vista previa / Historial / Etiquetas | `GET`/`POST` de lectura | **Sin control de permiso** (lectura) |
| Tipos de documento | Nuevo tipo / Editar / Desactivar | `/documents/types/` | `scope.assign` con alcance sobre la institución (previsto `document_type.manage`, ADR-0011) |
| Documentos del expediente | Descargar | `POST /documents/records/{id}/download-tokens/` | `document.read` con alcance |
| Documentos del expediente | Subir versión / escaneado (aún sin UI) | `/records/{id}/versions/`, `/records/scan/` | **Sin control de permiso en la vista**; revisar servicio |

## Estructura académica y operación (Persona 2)

| Pantalla | Acción (botón) | Endpoint | Permiso que exige el backend |
| --- | --- | --- | --- |
| Ciclo escolar | Nuevo ciclo / Crear ciclo | `POST /academics/cycles/` | `scope.assign` con alcance sobre la institución |
| Ciclo escolar | Activar | `POST /academics/cycles/{id}/activate/` | `scope.assign` con alcance sobre la institución |
| Ciclo escolar | Cerrar ciclo | `POST /academics/cycles/{id}/close/` | `scope.assign` con alcance sobre la institución |
| Ciclo escolar | Clonar estructura | `POST /academics/cycles/{id}/clone/` | `scope.assign` con alcance sobre la institución |
| Ciclo escolar | Editar (borrador) | `PATCH /academics/cycles/{id}/` | `scope.assign` con alcance sobre la institución |
| Ciclo escolar | Reabrir (ciclo cerrado; listado y detalle) | `POST /academics/cycles/{id}/reopen/` | `academic_cycle.reopen` con alcance sobre la institución |
| Ciclo escolar | Volver a borrador (D3; ciclo activo; listado y detalle) | `POST /academics/cycles/{id}/revert-to-draft/` | `academic_cycle.revert` con alcance sobre la institución (ni `scope.assign` ni `academic_cycle.reopen` lo sustituyen) |
| Ciclo escolar | Lista de verificación y botones deshabilitados | `GET /academics/cycles/{id}/readiness/` | **Sin control de permiso** (lectura, igual que el detalle) |
| Ciclo escolar → Secciones | Nueva sección / Editar / Desactivar (solo en borrador) | `POST /academics/sections/`, `PATCH`/`DELETE /academics/sections/{id}/` | `scope.assign` con alcance sobre la institución |
| Ciclo escolar → Plan de estudios | Agregar curso / Generar desde cursos del nivel / Marcar obligatorio u optativo / Quitar (solo en borrador) | `/academics/curriculum-plans/…` | `scope.assign` con alcance sobre la institución |
| Ciclo escolar → Asignaciones | Matriz; Asignar por celda; Reemplazar docente | `GET …/assignment-matrix/`, `POST …/teaching-assignments/batch/`, `POST /teaching-assignments/{id}/reassignments/` | `scope.assign` con alcance sobre la institución (sin el permiso la pestaña lo explica y no consulta) |
| Ciclo escolar → Horarios | Nuevo bloque / Editar / Desactivar; Agregar y quitar clase; Copiar horario; Publicar / Despublicar | `/shifts/{id}/schedule-blocks/`, `/schedule-blocks/{id}/`, `/sections/{id}/class-sessions/…`, `/class-sessions/{id}/`, `/cycles/{id}/schedule-publication/` | `scope.assign` con alcance sobre la institución (las lecturas solo exigen sesión) |
| Ciclo escolar | Días no computables: ver / declarar / quitar | `GET`/`POST /academics/cycles/{id}/non-computable-days/`, `DELETE /academics/non-computable-days/{id}/` | Ver: sesión. Declarar y quitar: `scope.assign` con alcance sobre la institución |
| Ciclo escolar | Ver detalle histórico | `GET /academics/cycles/{id}/` | **Sin control de permiso** (lectura) |
| Sedes | Nueva sede / Editar / Desactivar; Nueva jornada / Editar / Desactivar | `/academics/campuses/`, `/campuses/{id}/shifts/`, `/shifts/{id}/` | `scope.assign` con alcance sobre la institución |
| Aulas | Nueva aula / Editar / Desactivar | `/academics/classrooms/` | `scope.assign` con alcance sobre la institución |
| Niveles | Nuevo nivel / Editar / Desactivar; Nuevo grado / Editar / Desactivar; Vincular / Desvincular curso | `/academics/levels/…`, `/grades/…`, `/level-subjects/…` | `scope.assign` con alcance sobre la institución |
| Cursos | Nuevo curso / Editar / Desactivar | `/academics/subjects/` | `scope.assign` con alcance sobre la institución |
| Asignaciones docentes | Nueva asignación / Asignar por lotes / Clonar en ciclo nuevo | `POST /academics/teaching-assignments/`, `POST /academics/cycles/{id}/teaching-assignments/batch/` | `scope.assign` con alcance sobre la institución |
| Asignaciones docentes | Listado, matriz sección × curso, vista previa del clonado | `GET /academics/teaching-assignments/`, `GET /academics/cycles/{id}/assignment-matrix/`, `GET /academics/cycles/{id}/teaching-assignments/clone-preview/` | `scope.assign` con alcance sobre la institución |
| Asignaciones docentes | Reasignar a otro docente | `POST /academics/teaching-assignments/{id}/reassignments/` | `scope.assign` con alcance sobre la institución |
| Evaluación | Nueva unidad / Crear unidad | `POST /academics/cycles/{id}/evaluation-units/` | `evaluation.configure_units` con alcance sobre la institución (#631; antes solo sesión) |
| Evaluación | Ajustar ventana de recuperación | `PATCH …/evaluation-units/{id}/recovery-window/` | `evaluation.configure_units` con alcance sobre la institución (#631) |
| Evaluación | Cerrar unidad | `PATCH …/evaluation-units/{id}/close/` | `evaluation.configure_units` con alcance sobre la institución |
| Evaluación | Permisos excepcionales de captura → Otorgar excepción / listado | `GET`/`POST …/evaluation-units/{id}/capture-exceptions/` | `evaluation.configure_units` con alcance sobre la institución (#631) |
| Evaluación | Cambiar configuración / Guardar default | `PATCH /academics/evaluation-config/`, `PATCH /academics/cycles/{id}/evaluation-config/` | `evaluation.configure_units` con alcance sobre la institución (#631); la consulta (`GET`) sigue con sesión |
| Evaluación | Clonar configuración | `POST /academics/cycles/{id}/evaluation-config/clone/` | `evaluation.configure_units` con alcance sobre la institución |
| Evaluación | Notas de la unidad → Registrar nota | `POST …/evaluation-units/{id}/grades/` | `grade.write` con alcance (asignación docente) |
| Evaluación | Planilla de calificaciones → abrir | `GET …/evaluation-units/{id}/sheet/` | `grade.write` sobre la sección y la subárea, o `evaluation.configure_units` sobre la institución (solo lectura) |
| Evaluación | Planilla → Guardar / Cargar archivo | `POST …/grades/sheet/`, `POST …/grades/bulk/` | `grade.write` sobre la sección y la subárea |
| Evaluación | Avance de captura | `GET …/evaluation-units/{id}/capture-progress/` | `evaluation.configure_units` (todas las filas) o `grade.write` con asignaciones vigentes (solo las propias) (#631) |
| Evaluación | Recuperación → elegibilidad (matrícula o sección) | `GET …/enrolments/{id}/recovery-eligibility/`, `GET …/sections/{id}/recovery-eligibility/` | `student.view_basic` con alcance sobre el estudiante o la sección (#631) |
| Evaluación | Recuperación → Registrar nota | `POST …/enrolments/{id}/recovery-grades/` | `grade.write` sobre la sección y la subárea (#631) |
| Evaluación | Boleta del estudiante | `GET …/enrolments/{id}/grades/` | `student.view_basic` con alcance sobre el estudiante |
| Evaluación | Resultados congelados (consulta y listado) | `GET …/subjects/{id}/frozen-result/`, `GET …/enrolments/{id}/frozen-results/`, `GET …/frozen-promotion/` | **Sin control de permiso** (solo sesión; #643) |
| Evaluación | Corregir resultado congelado | `POST …/frozen-result/correct/` | `grade.correct` (sin alcance) |
| Evaluación | Consultar nota final / promedio; listado de notas de la unidad | `GET` de consulta | **Sin control de permiso** en la vista (el listado de notas sí acota al docente a sus asignaciones; #643) |
| Asistencia | Escanear | `POST /attendance/scan/` | `attendance.scan` **y** `attendance.record_entry` o `attendance.record_exit` (composición) |
| Asistencia | Registrar movimiento | `POST /attendance/events/` | permiso del origen (`attendance.scan`, `attendance.record_manual` o `attendance.declared_close`) **y** del tipo (`attendance.record_entry`/`attendance.record_exit`), más `student.view_basic` con alcance |
| Asistencia | Parámetros de jornada → Registrar parámetros | `POST /attendance/jornada-parameters/` | `attendance.jornada.configure` |
| Asistencia | Cierre de sección → Cerrar | `POST /attendance/section-closures/` | `attendance.declared_close` **y** `attendance.record_exit` |
| Asistencia | Cierre de sección → Previsualizar | `GET /attendance/section-closures/preview/` | **Sin control de permiso** |
| Asistencia | Presencia, estado del día, porcentaje | `GET` de consulta | `student.view_basic` con alcance |
| Asistencia | Cámara | sin endpoint | — |
| Alertas | Atender | `POST /reporting/alerts/{id}/acknowledge/` | `reporting.alert.acknowledge` y `student.view_basic` con alcance |
| Alertas | Evaluar alertas | `POST /reporting/alert-evaluations/` | `reporting.alert.evaluate` |
| Alertas | Umbrales → Registrar umbral | `POST /reporting/absence-threshold-parameters/` | `reporting.absence_threshold.configure` |

Las pantallas de Persona 1 (Cuentas, Roles, Auditoría, Plataforma, Mi cuenta)
ya aplican esta regla.

## Pendiente por dueño

Los huecos del backend de ambas listas se siguen en [#643](https://github.com/siga-inebi/siga-inebi/issues/643); aquí solo se
resume qué toca a cada dueño.

**Persona 2** (Ciclos, Sedes, Aulas, Niveles, Cursos, Asignaciones,
Evaluación, Asistencia):

- Aplicar `<Can>` / `usePermissions` a **todas** las acciones de sus módulos
  según la tabla: ningún botón visible sin su permiso. Hecho en #631 para
  Ciclo escolar (con sus pestañas), Sedes, Aulas, Niveles, Cursos y
  Asignaciones docentes; quedan Evaluación y Asistencia.
- Cerrar en el backend los huecos marcados "Sin control de permiso" en
  la previsualización del cierre de sección, con denegación por defecto. En
  Evaluación, #631 cerró la configuración (`evaluation.configure_units`), el
  avance de captura y la recuperación; quedan las consultas de nota final,
  promedio, listado de notas y resultados congelados (#643).

**Persona 3** (Estudiantes, Docentes, Padres, Personas, Matrículas,
Plantillas, Tipos de documento, Documentos):

- Aplicar `<Can>` / `usePermissions` a **todas** las acciones de sus módulos
  según la tabla.
- Exigir en el backend `person.view` / `person.edit` en `apps/people` y
  `document_type.manage` en los tipos de documento (permisos ya creados en el
  catálogo, ADR-0011). Hasta entonces el filtro del menú para Personas y Tipos
  de documento es **provisional y solo de presentación**.
- Cerrar los huecos "Sin control de permiso" de Docentes y Padres de familia
  (alta, edición y listado) con denegación por defecto.
