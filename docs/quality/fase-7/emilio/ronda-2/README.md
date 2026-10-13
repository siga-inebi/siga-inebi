# Segunda ronda de asistencia y credencial de Emilio

Corridas `RUN-EMI-20261012-04` y `RUN-EMI-20261012-05`, ejecutadas el 12 de octubre de 2026 (America/Guatemala) sobre `4bf2b543ab669646045f102c200047fff121f904` (árbol limpio al ejecutar), rama `docs/qa-emilio-ronda-2` creada desde la primera ronda. Responsable: Emilio; ejecución técnica asistida por Claude Code; revisión cruzada de Josué pendiente.

Objetivos: cubrir RF-JOR-007, que quedó sin evidencia en la [primera ronda](../README.md), y medir la frecuencia del fallo intermitente INC-010.

| Corrida | Alcance | Casos | Resultado |
| --- | --- | ---: | --- |
| RUN-EMI-20261012-04 | `reporting`: alertas de asistencia (RF-JOR-007) | 28 | **28 aprobadas**, 0 fallidas. Exit code 0. 20 unitarias, 6 de API y 2 de integración; 17,79 s. |
| RUN-EMI-20261012-05 | Selección backend de la primera ronda repetida 10 veces | 10 × 302 | **9 iteraciones sin fallos; 1 iteración con 1 fallo** (3 020 ejecuciones de caso, 3 019 aprobadas). |

PostgreSQL 16.11, Python 3.11.15, Django 5.2.17, pytest 8.4.1; entorno Docker `backend-test` en Linux (WSL2), configuración `config.settings.test`, datos sintéticos creados por factories; proyecto aislado `siga_inebi_emilio_qa`.

## RF-JOR-007: las pruebas aprueban, pero no verifican el criterio

El criterio de aceptación es: *"El padre recibe una notificación cuando su hijo registra una inasistencia."*

Las 28 pruebas de `reporting` verifican alertas de ausencia no registrada, ausencias frecuentes según umbral versionado, proyección de alertas de asistencia, atención de alertas y evaluación diaria combinada. Todas aprueban. Sin embargo:

- `reporting.Alert.TargetRole` solo admite `control_point` y `section_coordinator` (`backend/apps/reporting/models.py:72-74`). Los servicios crean las alertas de ausencia con `target_roles=[Alert.TargetRole.SECTION_COORDINATOR]` (`backend/apps/reporting/services.py:250` y `:324`).
- El propio código lo declara: *"every other alerting surface (`AttendanceAlert`, `reporting.Alert`) targets school staff, never a guardian"* (`backend/apps/attendance/models.py:522-531`). El único canal hacia el encargado es `JustificationNotification`, que corresponde a RF-JUS-006 (resolución de justificaciones), no a inasistencias.
- Ninguna de las 28 pruebas menciona encargado ni padre.

Conclusión: la evidencia cubre alertas al **personal**, no la notificación al **encargado** que exige el criterio. `traceability-matrix.md` marca el requisito como `Implemented`. Se registra como **INC-012** para decisión de Pablo: implementar la notificación o aprobar explícitamente un alcance reducido. Esta ronda no cambia el estado del requisito.

| Prueba representativa | Qué verifica |
| --- | --- |
| `tests/unit/test_reporting_services.py::test_no_entry_after_limit_time_generates_absence_alert_for_coordinator` | Sin ingreso al vencer el límite se genera alerta de ausencia **para el coordinador**. |
| `tests/unit/test_reporting_services.py::test_absence_alert_not_raised_before_entry_limit_time_elapses` | No hay alerta antes del límite de ingreso. |
| `tests/unit/test_reporting_services.py::test_frequent_absences_over_threshold_generates_alert` | Ausencias frecuentes sobre el umbral generan alerta. |
| `tests/integration/test_reporting.py::test_absence_alert_end_to_end_with_real_enrolment_and_section_coordinator_targeting` | Flujo con matrícula real; alerta dirigida al coordinador de sección. |

El detalle de las 28 pruebas está en [resultados.csv](resultados.csv).

## INC-010: frecuencia del fallo intermitente

| Iteración | Resultado | Prueba fallida |
| ---: | --- | --- |
| 1–2, 4–10 | 302/302 | — |
| 3 | 301/302 | `tests/api/test_attendance_api.py::test_updating_jornada_parameters_does_not_change_earlier_days_derived_status` (`KeyError: 'status'`: la respuesta no fue el estado diario) |

Detalle por iteración en [iteraciones.csv](iteraciones.csv).

Contando ambas rondas, **2 de 12 corridas completas** sobre el mismo código fallaron con un único caso cada una, y **cada vez fue una prueba distinta**:

- RUN-EMI-20261012-01: `test_close_jornada_creates_alert_for_permanence_without_closure` (`GET attendance/alerts/` → 403).
- RUN-EMI-20261012-05, iteración 3: `test_updating_jornada_parameters_does_not_change_earlier_days_derived_status`.

Patrón común: ambas otorgan alcance sobre el estudiante con `_grant_student_scope` (factory con `starts_at = timezone.now()`) y en seguida consultan un endpoint que resuelve alcance con `starts_at__lte=timezone.now()` (`backend/apps/identity/scopes.py:28-41`, `backend/apps/identity/models.py:131-134`). La lógica es correcta si el reloj solo avanza. El orden de pytest es el mismo en todas las corridas, así que la causa no es el orden de ejecución.

**Hipótesis, sin verificar:** un retroceso puntual del reloj de pared, por ejemplo la resincronización de hora de WSL2 con el anfitrión, deja un `starts_at` recién creado "en el futuro" y la consulta se deniega. Explicaría que falle una prueba distinta cada vez. Para confirmarla: repetir en el CI de GitHub (Linux nativo) o en otro equipo, y medir saltos de `time.time()` dentro del contenedor. Mitigación posible en las pruebas, como cambio separado: crear las factories con `starts_at` unos segundos en el pasado. No se modificó código en esta ronda.

INC-010 se mantiene abierta (S3) y su registro se amplía con la segunda prueba afectada.

## Seguimiento del 13/10: causa de INC-010

Corrida `RUN-EMI-20261013-01`, 13 de octubre de 2026, 06:30–06:34 (America/Guatemala), sobre `df50384313057d596d5415b301b6e1bbef90f053` (árbol limpio), misma selección backend repetida 10 veces. Objetivo: descartar la hipótesis de Daniel (comparación entre fecha local y UTC), ya que las 12 corridas anteriores fueron entre 20:08 y 20:55, cuando la fecha UTC ya era el día siguiente. En esta corrida ambas fechas coinciden.

| Resultado | Detalle |
| --- | --- |
| Iteraciones | 7 sin fallos; 3 con fallos (4 casos en total) |
| Iteración 2 | `test_current_capture_batch_endpoint_recovers_pending_batch_with_original_capture_times` (`KeyError: 0`) |
| Iteración 3 | `test_scan_confirmation_p95_latency_is_within_two_seconds` (403) y `test_peak_concurrent_operators_scan_without_contention_or_lost_events` (403: *"El actor no tiene el permiso requerido."*) |
| Iteración 8 | `test_justification_attachment_upload_endpoint_succeeds_for_the_submitter` (403) |

Detalle por iteración en [iteraciones.csv](iteraciones.csv), filas `RUN-EMI-20261013-01`.

**La hipótesis de fecha local/UTC queda descartada:** falla igual con ambas fechas iguales, y la verificación de permiso y alcance compara marcas de tiempo (`starts_at <= timezone.now()`), no fechas.

**Causa: el reloj de pared retrocede en el entorno WSL2.**

- Un complemento de diagnóstico (`inc010_probe.py`, solo en la carpeta de evidencia; no modifica pruebas) registró relojes al fallar. En las iteraciones 2 y 8, el `now()` de PostgreSQL —inicio de la transacción de la prueba— es 0,6 s y 1,1 s **posterior** al `timezone.now()` de Python tomado al final de la misma prueba. Con un reloj estable eso es imposible.
- `clock_watch.py`, ejecutado 120 s en el mismo contenedor, compara `time.time()` con `time.monotonic()`: el reloj de pared **retrocede cada 30 s** (a los 16,8; 46,8; 76,8 y 106,8 s) entre 0,87 y 1,76 s, y entre correcciones adelanta; deriva final −4,6 s. Es la sincronización de hora de la VM de WSL2 con Windows, que corrige por saltos. Resultado en `clock-watch.json`.
- Mecanismo: las pruebas crean `RoleAssignment`/`ScopeGrant` con `starts_at = timezone.now()` y en seguida consultan endpoints que exigen `starts_at <= timezone.now()` (`backend/apps/identity/models.py:131-134`, `backend/apps/identity/scopes.py:28-41`). Si un salto atrás cae entre ambos instantes, la asignación queda "en el futuro" y la consulta responde 403. Por eso falla una prueba distinta cada vez y la frecuencia no depende del orden.
- Los 403 de esta corrida dicen "permiso", no "alcance", y esos caminos no auditan la denegación, por lo que la sonda no registró `AuditEvent`; las marcas de tiempo bastan para la conclusión.

**Clasificación:** defecto del entorno de ejecución local, no del producto. En el CI de GitHub (Linux nativo), el job `backend-tests` —suite completa, que incluye estas pruebas— aprobó en las últimas 30 ejecuciones del flujo `ci.yml` consultadas el 13/10, sin ningún fallo. Opciones, a decidir por el equipo y en un cambio separado:

1. Entorno: reiniciar WSL (`wsl --shutdown`) o ajustar la sincronización de hora del equipo; reduce los saltos pero no garantiza su ausencia.
2. Pruebas: que las factories de identidad creen `starts_at` unos segundos en el pasado. Hace la suite inmune a saltos pequeños sin tocar lógica de producto.

No se modificó código en esta ronda. INC-010 pasa a **Causa identificada**.

## Reproducción

Desde la raíz del repositorio, con Docker activo. La carpeta de evidencia necesita permiso de escritura para el usuario del contenedor.

```bash
docker compose -p siga_inebi_emilio_qa -f compose.yml -f compose.test.yml build backend-test
docker compose -p siga_inebi_emilio_qa -f compose.yml -f compose.test.yml up -d db-test
# RUN-04
docker compose -p siga_inebi_emilio_qa -f compose.yml -f compose.test.yml run --rm -v <absolute-evidence-directory>:/evidence backend-test sh /evidence/run.sh
```

Los scripts exactos (`run.sh`) de cada corrida están en su carpeta de evidencia y se identifican por hash en [evidencias.md](evidencias.md). RUN-05 ejecuta la selección de la primera ronda en un ciclo de 10 iteraciones con `--junitxml=/evidence/junit-N.xml`. No se midió cobertura porcentual (`--no-cov`).

## Trazabilidad

`docs/requirements/traceability-matrix.md`: en RF-JOR-007 se reemplaza `TBD` por `#343`, el PR fusionado que creó `reporting` y sus pruebas (commit `7fe68d0`). No se cambia el estado del requisito.

## Límites y pendientes

- La decisión sobre RF-JOR-007 (INC-012) corresponde a Pablo y al responsable de alcance.
- INC-010: causa identificada (saltos atrás del reloj de WSL2, ver seguimiento del 13/10); falta decidir la mitigación.
- INC-011 (catálogos paginados sin orden) sigue abierta; su corrección es un cambio de código y va en un PR propio.
- Siguen pendientes de la primera ronda: flujo manual CP-INT-ASI-001 con Josué y CP-INT-JUS-001 con Diana, cámara real, medición visual con Daniel y PD-010.
- No se declara UAT aprobada ni se cierran requisitos.
