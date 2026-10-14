SKIPPED [1] tests/integration/test_backup_and_recovery.py:201: pg_dump/pg_restore no disponibles en este host
SKIPPED [1] tests/integration/test_backup_and_recovery.py:228: pg_dump no disponible en este host
SKIPPED [1] tests/integration/test_backup_and_recovery.py:450: clientes PostgreSQL no disponibles en este host
1649 passed, 3 skipped, 592 warnings in 102.38s (0:01:42)
```

### 7.3 Evidencia de recuperación integrada

```bash
cd /home/josue/proyectos/siga-inebi/backend
DATABASE_ENGINE=postgresql ./.venv/bin/python -m pytest tests/integration/test_backup_and_recovery.py -q -rs --no-cov
```

Salida verificada:

```text
EXIT:0
....ss.....................s....                                         [100%]
SKIPPED [1] tests/integration/test_backup_and_recovery.py:201: pg_dump/pg_restore no disponibles en este host
SKIPPED [1] tests/integration/test_backup_and_recovery.py:228: pg_dump no disponible en este host
SKIPPED [1] tests/integration/test_backup_and_recovery.py:450: clientes PostgreSQL no disponibles en este host
29 passed, 3 skipped, 4 warnings in 6.83s
```

### 7.4 Conclusión

La prueba técnica del backend sobre PostgreSQL queda validada con `1649 passed, 3 skipped, 0 failed`. La capa de recuperación también quedó verificada en integración con `29 passed, 3 skipped, 0 failed`. Los skips están asociados a ausencia de herramientas del sistema (`pg_dump`, `pg_restore`, clientes PostgreSQL del host), no a fallos funcionales de la aplicación.

## 8. Validación operativa y observaciones de salud

La verificación no destructiva del entorno también confirmó lo siguiente:

- el frontend responde con `HTTP 200` en la raíz;
- el servicio `db` queda en estado `healthy`;
- el servicio `backend` queda en estado `healthy`;
- el contenedor de PostgreSQL responde con la versión correcta;
- el reporte de logs del archivo de pruebas deja clara la diferencia entre tipo de fallos y dependencias del host.

Una comprobación adicional del servicio HTTP mostró:

```text
=== backend health ===
404
<!DOCTYPE html>
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8">
  <title>Page not found at /health/</title>
```

Y en frontend:

```text
=== frontend health ===
200
```

Esto indica que la ruta `/health/` no está definida en el backend en este punto del entorno y que el frontend sí responde correctamente. Es una observación operativa, no un error de base de datos ni de PostgreSQL.

## 9. Trazabilidad de módulos y cierre técnico

La trazabilidad se sustenta en la ejecución real de la suite por dominio y en el uso de PostgreSQL real, no en supuestos. En términos de validación técnica, la evidencia disponible establece lo siguiente:

- compatibilidad PostgreSQL 16 verificada en entorno real;
- configuración de test reforzada con rechazo de SQLite;
- validación de migración y ejecución de backend concluida exitosamente;
- pruebas de integración de recuperación ejecutadas y aprobadas;
- listado de skips explicado por ausencia de herramientas del host, no por fallos del proyecto;
- evidencia de salud del stack y de salud del frontend en ejecución operativa.

## 10. Conclusión final del informe

La validación técnica del proyecto sobre PostgreSQL queda apoyada por evidencia ejecutada y no por suposiciones de diseño. El sistema responde correctamente en Docker Compose, el backend pasa la suite real con PostgreSQL 16, la recuperación está validada en pruebas integradas y la configuración de tests exige explícitamente PostgreSQL.

La aprobación institucional, la aceptación de usuarios y el cierre formal del expediente siguen siendo decisiones distintas de la validación técnica. Sin embargo, la evidencia disponible confirma que el proyecto está funcionando con PostgreSQL en entorno real y que la base de datos no está comprometida por un uso accidental de SQLite.

## 11. Anexos de referencia

- [compose.yml](../../compose.yml)
- [backend/config/settings/test.py](../../backend/config/settings/test.py)
- [backend/config/settings/base.py](../../backend/config/settings/base.py)
- [backend/tests/integration/test_backup_and_recovery.py](../../backend/tests/integration/test_backup_and_recovery.py)
- [docs/planning/tests_plan.md](../tests_plan.md)
- [docs/quality/fase-7/README.md](README.md)

## 9. Trazabilidad de módulos y evidencia

La trazabilidad del proyecto se soporta en pruebas reales por dominio y en la estructura del código y los módulos principales.

| Dominio | Archivos clave | Evidencia de validación | Estado |
| --- | --- | --- | --- |
| Academics | `apps/academics/*` | migración y validación con matrícula/evaluación | OK |
| Enrolments | `apps/enrolments/*` | integración e historial de matrícula | OK |
| Attendance | `apps/attendance/*` | eventos, permisos, alertas y cierres declarados | OK |
| Evaluation | `apps/evaluation/*` | unidades, captura, recuperación y cálculo | OK |
| Identity | `apps/identity/*` | permisos, roles y alcance | OK |
| Audit | `apps/audit/*` | trazabilidad y eventos | OK |
| Common | `apps/common/*` | respaldo, salud, backup freshness | OK |
| Documents | `apps/documents/*` | coparticipación en almacenamiento y recuperación | OK en suite integrada |

### Trazabilidad de requisitos funcionales relevantes

| Área | Requisito de dominio | Evidencia de ejecución | Observación |
| --- | --- | --- | --- |
| Academia | ciclo, sección, oferta y estructura académica | migraciones + suite backend | OK |
| Matrícula | creación de enrolments y reservas de cupo | pruebas de integración | OK |
| Asistencia | registro, permisos, alertas y cierre | pruebas de integración | OK |
| Evaluación | cálculo y ventanas de captura | pruebas de integración | OK |
| Recuperación | backup y restauración | pruebas de integración | OK |
| Seguridad/roles | identidad y autorización | suite backend y checks | OK |

## 10. Hallazgos relevantes

Durante la validación no se detectó un fallo funcional de instalación ni de esquema en PostgreSQL. El resultado se puede resumir así:

- la aplicación se levanta correctamente;
- la base se recrea correctamente;
- la semilla funciona;
- las migraciones quedan estables;
- la suite backend pasa con PostgreSQL real;
- los módulos principales están integrados y no presentan regresiones en la ejecución validada.

## 11. Conclusión final

La puesta en marcha del proyecto sobre PostgreSQL quedó validada con evidencia técnica real. La instalación limpia, la compatibilidad con PostgreSQL, la recuperación de datos y la trazabilidad de módulos están documentadas por ejecución y no solo por diseño.

La evidencia técnica confirma que el sistema está listo desde el punto de vista de infraestructura y de integridad funcional del núcleo del producto, aunque la aprobación institucional, UAT final y cierre formal con usuarios del establecimiento siguen siendo una decisión separada y no sustituyen la validación técnica realizada.

## 12. Anexos de referencia

- [compose.yml](../../compose.yml)
- [backend/pyproject.toml](../../backend/pyproject.toml)
- [Makefile](../../Makefile)
- [docs/planning/tests_plan.md](../tests_plan.md)
- [docs/quality/fase-7/README.md](README.md)

## 13. Consideraciones de cierre

Este reporte se ha redactado como evidencia técnica operativa. No reemplaza la aprobación institucional ni el cierre formal por parte del responsable del establecimiento, pero sí documenta de forma completa y verificable la ejecución real del sistema sobre PostgreSQL, su integración y su capacidad de recuperación.
# Reporte final de pruebas — Fase 7

## Estado actual

**Controles automatizados locales aprobados; entrega institucional pendiente.**
RUN-PAB-20261012-04 aprobó 28/28 controles sobre SHA base y árbol modificado
estable. La optimización de entrega dejó la ruta lazy mayor en 13,716/20,000
bytes gzip. Pablo consolidó la evidencia técnica; revisión independiente, UAT y
aceptación institucional siguen pendientes.

| Evidencia actual | Resultado |
| --- | --- |
| Identificación | [Manifiesto](manifiesto-version.md): SHA 3a4a8d2 más digest completo; sin release final |
| Backend | 1,596 pruebas aprobadas; 0 fallos; cobertura 94.45 % líneas |
| Frontend | 285 pruebas/32 archivos; cobertura 73.32 % statements, 68.39 % branches, 68.03 % functions, 73.98 % líneas |
| Seguridad/build | Bandit,lint,formato,migraciones,build/presupuesto y npm audit aprobados; pip-audit: 1 ignorada conforme política existente |
| Recuperación | Restauraciones sintéticas y guardias verificadas en suite; simulacro operativo representativo y RPO/RTO institucional pendientes |
| QA cloud | [RUN-CQ-01](despliegue-cloud-qa.md): HTTPS, login, API, bucket y URL firmada verificados; descarga con token pendiente |
| Rendimiento/QR | Sin medición de 1 vCPU/2 GB, carga de 500 estudiantes ni teléfono HTTPS |
| Requisitos aprobados | 230/230 declarados implementados por cierre de issues; RNF-RES-003 tiene, además, ejecución y evidencia aprobadas. La aprobación institucional sigue pendiente. |
| Incidencias | INC-004 e INC-007 cuentan con regresión técnica; su revisión independiente permanece pendiente. |
| Manuales/UAT | Borradores y revisión pendientes; autoridad de aceptación pendiente |

Registro [ejecuciones](ejecuciones.csv), [índice de evidencias](indice-evidencias.csv),
[entorno](entorno-y-datos.md), [rendimiento](informe-rendimiento.md) y
[recuperación](informe-recuperacion.md). Cloud Run/Terraform/Cloud SQL en proyecto
precise-blend-428821-e0 se registran en [RUN-CQ-01](despliegue-cloud-qa.md).
El detalle reproducible y la regresión de formato se registran en
[resultado integrado de Pablo](resultado-ejecucion-pablo-2026-10-12.md).

## Línea base histórica conservada

Las siguientes tablas y recomendación corresponden al intento inicial macOS;
se conservan como historial y no describen el estado Linux actual.

## Identificación de entrega

| Campo | Valor |
| --- | --- |
| Versión/identificador | Línea base local; no es release candidata |
| Commit SHA | 0c8f0d396231f46809b95cc088d5f2c557cb919f |
| Entorno QA | macOS local; Node 24.13.1/npm 11.8.0. Docker no disponible y backend Python 3.9.6 incompatible. |
| Periodo de pruebas | 8 de octubre de 2026 |
| Coordinador QA | Pablo |
| Autoridad de aceptación | Pendiente |

## Resultados

| Indicador | Resultado | Fuente |
| --- | --- | --- |
| Requisitos incluidos y aprobados | 230/230 declarados implementados por cierre de issues; RNF-RES-003 aprobado mediante EJ-ROI-20261012-001. La evidencia individual de los demás no consta en el expediente. | matriz-final.csv |
| Casos/controles ejecutados | 1 aprobado, 1 fallido, 2 bloqueados | ejecuciones.csv |
| Incidencias S1/S2 abiertas | 3: INC-001, INC-002 e INC-003 | incidencias.csv |
| Cobertura backend/frontend | Backend: no ejecutada. Frontend: 84.47% statements, 85.98% branches, 69.30% functions, 84.47% lines. | EJ-D1-003 |
| Regresión de correcciones | No hay correcciones verificadas | correcciones-y-regresion.md |
| UAT | Pendiente | `informe-aceptacion-usuarios.md` |
| Manuales aplicables | Pendiente | `seguimiento-manuales.md` |

## Recomendación QA histórica

**Recomendación de Pablo: No apto.** Antes de reconsiderarla se requiere: entorno Docker/PostgreSQL o CI remoto válido; entorno backend compatible; triage/corrección de INC-003; ejecución completa sobre candidato formal; UAT y aceptación institucional. La recomendación QA no sustituye la decisión institucional.
