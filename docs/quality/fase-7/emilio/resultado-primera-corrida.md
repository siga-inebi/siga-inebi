# Resultado de la primera corrida de asistencia y credencial

| Corrida | Alcance | Casos | Aprobados | Fallidos | Omitidos | Exit code | Estado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| RUN-EMI-20261012-01 | Backend: unitarias, API, permisos e integración de asistencia/credencial | 302 | 301 | 1 | 0 | 1 | Fallido |
| RUN-EMI-20261012-02 | Frontend: asistencia, cámara y lote | 27 | 27 | 0 | 0 | 0 | Aprobado |
| RUN-EMI-20261012-03 | Backend, diagnóstico: misma selección y SHA que la 01 | 302 | 302 | 0 | 0 | 0 | Aprobado |

La corrida 01 se conserva como fallida. La 03 no la sustituye: clasifica el fallo como intermitente (INC-010).

## RUN-EMI-20261012-01 — backend

- 302 casos: 160 unitarios, 120 de API, 3 de permisos y 19 de integración.
- Fallo: `tests/api/test_attendance_api.py::test_close_jornada_creates_alert_for_permanence_without_closure`. El cierre de jornada respondió 200 con una alerta `permanencia_sin_cierre` dirigida a `control_point` y `section_coordinator`, como se esperaba. La consulta posterior `GET attendance/alerts/` respondió 403 (`assert 403 == 200`, línea 399).
- Pytest reportó 52,89 s y siete advertencias. Cuatro son `RemovedInDjango60Warning` por `CheckConstraint.check` en modelos y migraciones de academics y enrolments. Tres son `UnorderedObjectListWarning`: los catálogos de puntos de control, motivos de registro manual y motivos de justificación paginan sin orden estable (INC-011). Ninguna provocó fallos; se conservan en el log.
- Inicio UTC: 2026-10-13T02:08:34Z; fin UTC: 2026-10-13T02:09:40Z (20:08–20:09 del 12/10, America/Guatemala).

## RUN-EMI-20261012-02 — frontend

- 27 casos: `AttendancePage.test.jsx` 11, `CameraPreviewWindow.test.jsx` 6, `camera.test.js` 5 y `useBatchSubmit.test.jsx` 5.
- Vitest reportó 27,38 s. Incluye registro de movimiento, duplicado sin nuevo evento, reintento con el mismo `client_event_id`, verificación de permiso de cámara al entrar, rechazo por autorización y ausencia de datos del estudiante en el dispositivo.
- Inicio UTC: 2026-10-13T02:09:48Z; fin UTC: 2026-10-13T02:10:19Z.

## RUN-EMI-20261012-03 — diagnóstico backend

- Antes de esta corrida, la prueba fallida se ejecutó sola y aprobó (16,77 s).
- La selección completa aprobó 302 de 302 en 53,10 s, sin cambios de código ni de datos entre corridas.
- Inicio UTC: 2026-10-13T02:11:59Z; fin UTC: 2026-10-13T02:13:00Z.

## RUN-EMI-20261012-06 — regresión de INC-011

- Código: `0e1eb6c4354ac198ca05f4696cdddf648faeb3e4` (rama de esta ronda con los commits de revisión de Daniel: `ed65bd6` corrige INC-011 y `0e1eb6c` refactoriza `test_backup_and_recovery.py`).
- Misma selección backend que la corrida 01: **305 aprobadas, 0 fallidas** (302 previas más las 3 parametrizaciones de `test_catalogue_pagination_is_stable_across_pages`). Exit code 0; 53,62 s.
- Las tres advertencias `UnorderedObjectListWarning` desaparecen; quedan las cuatro `RemovedInDjango60Warning`.
- Inicio: 2026-10-12T21:22:21-06:00; fin: 2026-10-12T21:23:38-06:00 (America/Guatemala).
- INC-011 pasa a **En verificación**; su cierre queda pendiente de la revisión de Josué.

## Rendimiento direccional (incluido en 01 y 03)

| Prueba | Requisito | Duración 01 | Duración 03 | Resultado |
| --- | --- | ---: | ---: | --- |
| `test_scan_confirmation_p95_latency_is_within_two_seconds` | RNF-REN-001 | 2,505 s | 2,630 s | Aprobado: p95 de 20 solicitudes de escaneo ≤ 2 s |
| `test_peak_concurrent_operators_scan_without_contention_or_lost_events` | RNF-REN-002 | 1,701 s | 1,694 s | Aprobado: 3 operadores × 4 elementos, sin pérdidas ni duplicados |

La duración es la de toda la prueba, no el p95. Mide la latencia de la API en el entorno de desarrollo, no la confirmación visual en el perfil objetivo de 1 vCPU / 2 GB. No certifica RNF-REN-001 ni RNF-REN-002.

## Datos comunes

- SHA: `5ed5fd24d02f494053c53dbbbafe50a8412534e5`; `git status --porcelain` vacío al iniciar.
- Ejecutó: Claude Code para Emilio; revisión de Josué pendiente.
- Entorno: Linux (WSL2) con Docker; backend Python 3.11.15, Django 5.2.17, pytest 8.4.1 y PostgreSQL 16.11; frontend Node 22.23.2, Vitest 4.1.11 y jsdom.
- Datos: factories sintéticas y dobles de servicio, en una base de pruebas efímera (`tmpfs`) sin datos institucionales.
- Alcance: sin cobertura global (`--no-cov`), navegador real, cámara real ni aceptación institucional.
- Preparación: el primer intento de la corrida 01 no ejecutó pruebas porque el contenedor no podía escribir en la carpeta de evidencia (`Permission denied`). Se dieron permisos de escritura a la carpeta y se repitió. No es un fallo funcional.
- Al terminar se detuvo únicamente `db-test` del proyecto `siga_inebi_emilio_qa`. Los contenedores de ejecución se eliminaron con `--rm`. No se alteró la base de desarrollo.
- Ajeno a esta corrida: el contenedor `backend` de desarrollo no arranca porque `seed_demo_data` viola `evaluation_unit_no_overlapping_dates` con los datos ya presentes en la base local. Afecta solo al entorno local de desarrollo.

[Resultados por prueba](resultados-pruebas.csv) · [Evidencia revisada y hashes](evidencia-revisada.md)

Los 45 requisitos del catálogo siguen sin aceptación: aprobar las pruebas existentes no demuestra todos los criterios. Persisten las discrepancias y brechas documentadas en [la guía](README.md).
