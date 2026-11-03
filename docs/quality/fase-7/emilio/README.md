# Primera ronda de Emilio — asistencia, credencial y captura

Fecha: 12 de octubre de 2026, America/Guatemala.
Código evaluado: `5ed5fd24d02f494053c53dbbbafe50a8412534e5` (`develop`, árbol limpio al iniciar).
Responsable: Emilio. Ejecución técnica asistida por Claude Code; revisión de Josué pendiente.
Diagnóstico local; no constituye candidato formal, aceptación institucional ni UAT.

## Archivos de trabajo

- [Resultado de la primera corrida](resultado-primera-corrida.md) (incluye la regresión de INC-011, RUN-EMI-20261012-06): backend **301 aprobadas y 1 fallida** de 302 (RUN-EMI-20261012-01); la corrida de diagnóstico sobre el mismo SHA aprobó **302 de 302** (RUN-EMI-20261012-03). Frontend **27 de 27 aprobadas** (RUN-EMI-20261012-02). El fallo intermitente se registra como INC-010 y las advertencias de paginación sin orden como INC-011.
- [Catálogo inicial](catalogo-inicial.csv): 45 requisitos (RF-CRE-001 a 006, RF-ASI-001 a 014, RF-JOR-001 a 011, RF-JUS-001 a 009, RNF-CON-001/002, RNF-REN-001/002 y RNF-USA-001), criterio original, estado según `matriz-final.csv` y `traceability-matrix.md`, y referencias candidatas.
- [Inventario de pruebas](inventario-pruebas.csv): 329 casos (302 backend y 27 frontend) con el requisito citado en la prueba, cuando existe, y su línea.
- [Resultados por prueba](resultados-pruebas.csv): estado y duración de cada caso en las tres corridas, transcritos de JUnit.
- [Evidencia revisada](evidencia-revisada.md): comandos, versiones y hashes de los logs/JUnit locales. Los artefactos crudos no se publican en Git; su entrega a revisores está pendiente.
- [Segunda ronda](ronda-2/README.md): RF-JOR-007 (28 aprobadas; el criterio de notificación al encargado no está cubierto, INC-012) y frecuencia de INC-010 (1 fallo en 10 iteraciones).
- [Informe de rendimiento](rendimiento/README.md): protocolo completo (3 rondas, calentamiento, 102 confirmaciones por ronda) en escenarios pico y normal con el backend limitado a 1 CPU / 2 GB; 612 de 612 confirmados, p95 entre 170 y 222 ms, CPU, memoria y gráficas. Incluye la segunda medición del desfase del reloj en WSL2 (INC-010).
- El catálogo general y sus resultados históricos se conservan. Este catálogo complementario no aprueba requisitos ni modifica el alcance institucional.

## Primeros seis casos

Todos usan datos sintéticos de las factories existentes y una base PostgreSQL de pruebas efímera (proyecto aislado `siga_inebi_emilio_qa`). Ejecutor técnico: Claude Code, para Emilio; revisor propuesto: Josué. El estado inicial se reconstruye por los fixtures de pytest y sus transacciones; no se modifica la base de desarrollo. Las referencias son relativas a `backend/` salvo indicación.

| Caso | Requisito / fuente | Precondición y pasos | Resultado esperado | Prueba reutilizada |
| --- | --- | --- | --- | --- |
| CP-UNI-CRE-EMI-001 | RF-CRE-001, RF-CRE-003, RF-CRE-004, RF-CRE-005 | Emitir credencial a estudiante con matrícula activa; inspeccionar el identificador; revocarla con y sin motivo; reponerla; consultar eventos previos. | Identificador opaco sin datos personales; revocar exige motivo y actor, y una credencial revocada deja de resolver; la reposición genera otro identificador; los eventos y el estado diario anteriores no cambian. | `tests/unit/test_attendance_services.py::test_the_opaque_identifier_does_not_encode_any_personal_data`, `::test_revoke_credential_requires_a_reason`, `::test_a_revoked_credential_no_longer_resolves`, `::test_revoking_a_credential_does_not_alter_past_attendance_events_or_day_status`; `tests/unit/test_qr.py` |
| CP-API-ASI-EMI-002 | RF-ASI-002, RF-ASI-003, RF-ASI-006 | Con permiso de escaneo y sin él, enviar lectura de credencial vigente y de credencial revocada. | Movimiento registrado y confirmación con solo foto, nombre, grado y sección; sin permiso o con credencial revocada se rechaza y se audita. | `tests/unit/test_attendance_services.py::test_record_scan_batch_confirmation_includes_photo_name_grade_and_section`, `::test_a_revoked_credential_rejection_is_audited_with_the_student`; `tests/api/test_attendance_api.py::test_open_capture_batch_endpoint_requires_permission` |
| CP-API-ASI-EMI-003 | RF-ASI-004, RF-ASI-010, RNF-CON-001 | Escanear dos veces el mismo movimiento dentro de la ventana de supresión; reenviar con el mismo `client_event_id`. | El duplicado se rechaza, informa la hora del registro existente y se audita sin crear evento; el reenvío es idempotente; la base rechaza `client_event_id` repetido. | `tests/api/test_attendance_api.py::test_scan_endpoint_rejects_duplicate_and_reports_existing_captured_at`, `::test_scan_endpoint_resend_with_same_client_event_id_is_idempotent`; `tests/unit/test_attendance_services.py::test_duplicate_client_event_id_is_rejected_at_the_database_level` |
| CP-API-LOT-EMI-004 | RF-ASI-007, RF-ASI-008, RF-ASI-009, RNF-CON-002 | Abrir lote, registrar elementos, simular pérdida de red y recuperar el lote desde otro dispositivo; confirmar más tarde. | Lote recuperable con las horas originales de captura; origen y transmisión distinguibles; recuperación desde otro dispositivo autorizado; la confirmación tardía conserva `captured_at`. | `tests/api/test_attendance_api.py::test_current_capture_batch_endpoint_recovers_pending_batch_with_original_capture_times`, `::test_current_capture_batch_endpoint_recovers_from_a_different_device`; `tests/unit/test_attendance_services.py::test_record_scan_batch_preserves_scanned_captured_at_when_batch_confirms_later`; `frontend/src/test/useBatchSubmit.test.jsx` |
| CP-API-JOR-EMI-005 | RF-JOR-004, RF-JOR-005, RF-ASI-013 | Estudiante con ingreso y sin egreso; cerrar la jornada; consultar alertas; recalcular el día dos veces. | Permanencia sin cierre marcada y alerta para punto de control y coordinador; los eventos no se sobrescriben; recalcular es idempotente. | `tests/unit/test_attendance_services.py::test_close_jornada_flags_permanence_without_closure`, `::test_recalculate_day_is_idempotent`; `tests/api/test_attendance_api.py::test_close_jornada_creates_alert_for_permanence_without_closure` (intermitente, INC-010) |
| CP-UNI-JUS-EMI-006 | RF-JUS-003, RF-JUS-004, RF-JUS-006, RF-JUS-007 | Encargado envía justificación dentro y fuera de plazo; adjunta documento; docente aprueba y rechaza con y sin comentario. | Fuera de plazo se rechaza; rechazar exige comentario; ambas resoluciones notifican al encargado; solo quien la envió puede adjuntar, y solo un adjunto. | `tests/unit/test_attendance_services.py::test_submit_justification_outside_window_is_rejected`, `::test_resolve_justification_reject_requires_a_comment`, `::test_approving_a_justification_notifies_the_guardian_who_submitted_it`, `::test_attach_justification_document_rejects_a_non_submitter` |

El inventario enumera los nodos precisos. Las suites completas se ejecutaron, no solo estos casos. Revisar las aserciones por criterio antes de afirmar cobertura completa.

## Incidencias registradas en esta ronda

| ID | Hallazgo | Severidad | Estado |
| --- | --- | --- | --- |
| INC-010 | `tests/api/test_attendance_api.py::test_close_jornada_creates_alert_for_permanence_without_closure` falló una vez: el cierre de jornada respondió 200 con la alerta correcta, pero `GET attendance/alerts/` respondió **403** en lugar de 200. La misma prueba aprobó sola y la suite completa aprobó 302/302 en la corrida siguiente sobre el mismo SHA. Prueba intermitente dependiente del orden o del estado; causa no determinada. | S3 | Abierta |
| INC-011 | Los catálogos `attendance/control-points/`, `manual-registration-reasons/` y `justification-reasons/` paginan consultas sin orden (`UnorderedObjectListWarning` en `ControlPoint`, `ManualRegistrationReason` y `JustificationReason`). Dos páginas pueden repetir u omitir filas. Mismo patrón que INC-009 de Diana. Corregida por Daniel en `ed65bd6`; regresión aprobada en RUN-EMI-20261012-06. | S3 | En verificación |

## Brechas y decisiones para Pablo / Josué

1. **Estado desactualizado en la matriz.** `matriz-final.csv` clasifica 41 de los 45 requisitos como `Not implemented` / `Fuera del candidato actual`, pero `docs/requirements/traceability-matrix.md` los marca `Implemented` con PR fusionados (p. ej. #393, #399, #400, #454) y sus pruebas aprueban en esta ronda. Es la misma discrepancia que reportó Diana. Reconciliar; no se cambia el estado por una suite aprobada.
2. **Criterio duplicado.** `RF-ASI-001` ("Captura mediada por operador") tiene en el catálogo el mismo criterio de aceptación que `RF-JOR-001` (ventana operativa diaria). Corregir la fuente antes de evaluar el criterio.
3. **RF-JOR-010** no tiene criterio de aceptación ni fila en la matriz de trazabilidad. Requiere decisión de alcance.
4. **RF-JOR-007** (notificación al padre por inasistencia) tiene sus pruebas en `reporting` (`test_reporting_services.py`, `test_reporting_api.py`, `test_reporting.py`), fuera de esta selección. Incluirlas en la siguiente corrida.
5. **194 de 329 pruebas no citan un requisito** en su cuerpo; solo el docstring del archivo o ninguno. Para `RF-ASI-001`, `RF-JOR-001`, `RF-JOR-008`, `RF-JOR-009`, `RF-JOR-011` y `RNF-REN-002` el catálogo enlaza el archivo, no la función exacta. Asignarlas en la revisión cruzada.
6. **Rendimiento (RNF-REN-001/002).** `test_attendance_performance.py` aprobó (p95 ≤ 2 s con 20 solicitudes; 3 operadores × 4 elementos sin pérdidas ni duplicados), pero es evidencia direccional en entorno de desarrollo, no el perfil objetivo de 1 vCPU / 2 GB. Falta la medición lectura QR → confirmación visual con navegador y dispositivo real, TLS y el protocolo de §11 del plan (100 confirmaciones × 3 rondas), junto con Daniel. PD-010 (número de operadores y tasa pico) sigue sin respuesta institucional.
7. **Cámara (RNF-USA-001).** `camera.test.js`, `CameraPreviewWindow.test.jsx` y `AttendancePage.test.jsx` verifican el permiso antes del primer escaneo y la liberación del dispositivo, en jsdom con cámara simulada. Falta la prueba con cámara y dispositivo reales.
8. **Registro de incidencias.** `incidencias.csv` tiene dos filas con el mismo ID `INC-008` (Diana y Estuardo). Esta ronda usa `INC-010` para no colisionar; Pablo debe renumerar una de las dos.
9. Esta ronda usa `force_login`/`auth_client` y jsdom: no demuestra login real, CSRF, navegador, cámara, usabilidad ni UAT. `--no-cov` es intencional para un subconjunto.

## Siguiente sesión manual

Con Josué (CP-INT-ASI-001): matrícula activa → credencial → escaneo → evento → estado diario → consulta de presencia, con confirmación y denegaciones, en el QA integrado. Con Diana (CP-INT-JUS-001): encargado vinculado → solicitud → documento → revisión autorizada → efecto en jornada, conservando el evento original. Con Daniel: medición visual en dispositivo real. Registrar pasos, esperado/observado, SHA, evidencias e incidencias.

Cada resultado se entrega a Pablo y las evidencias técnicas a Daniel; Josué verifica la revisión cruzada.
