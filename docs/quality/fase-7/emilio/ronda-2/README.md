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
- INC-010: falta confirmar la hipótesis del reloj fuera de WSL2.
- INC-011 (catálogos paginados sin orden) sigue abierta; su corrección es un cambio de código y va en un PR propio.
- Siguen pendientes de la primera ronda: flujo manual CP-INT-ASI-001 con Josué y CP-INT-JUS-001 con Diana, cámara real, medición visual con Daniel y PD-010.
- No se declara UAT aprobada ni se cierran requisitos.
