# Operacion y Monitoreo

## Proposito

Describir como se observa la ejecucion de tareas en segundo plano y programadas,
y que puede consultar un administrador del sistema cuando algo no corrio.

`RNF-OPE-001` — *Registro de errores y monitoreo minimo del proceso trabajador y
de las tareas programadas* (prioridad MoSCoW: Debe). Regla de negocio asociada:
`RN-BIT-001`.

## Que hay hoy, y que no

`ADR-0009` difiere el proceso trabajador: no hay Redis, Celery ni cola, y
`RNF-REN-003` sigue en estado `Deferred`. Las tareas desatendidas de esta fase
son comandos de gestion de Django invocados por `cron`.

Este requerimiento no adelanta esa decision. Define el contrato de
observabilidad que cualquier ejecucion desatendida debe cumplir, y lo aplica a
las que existen. Cuando el worker llegue, instrumentar sus trabajos es usar el
mismo gestor de contexto, sin inventar un segundo mecanismo.

## Dos registros, un solo punto de escritura

Una tarea programada falla en silencio por omision: `cron` la lanza, el error
sale por la salida estandar de un contenedor que nadie mira, y el efecto se nota
semanas despues. Por eso hay dos registros complementarios, escritos desde
`apps/common/tasks.py::task_run` para que no puedan contar historias distintas:

| Registro | Donde | Responde |
| --- | --- | --- |
| Fila `common.TaskRun` | Base de datos | ¿Corrio? ¿Cuando? ¿Cuanto tardo? ¿Como termino? ¿Que conto? |
| Linea `siga.tasks` | Log de la consola | Detalle en vivo, con traceback completo del fallo |

La fila es la que contesta la pregunta dificil: **una tarea programada que no
dejo fila es una tarea que no corrio**. Un log no puede afirmar eso, porque la
ausencia de una linea y la ausencia del log son indistinguibles.

### Contrato de `TaskRun`

- Se escribe como `running` al iniciar y se cierra exactamente una vez.
- `summary` es un JSON libre que llena la propia tarea: contadores y totales que
  un administrador lee en tabla. Cada tarea se resume distinto y ninguna deberia
  necesitar un cambio de esquema para hacerlo.
- Un fallo guarda `error_type` y `error_message` (truncado a 2000 caracteres; el
  traceback completo queda en el log) **y conserva el resumen parcial**, que es
  lo que hace diagnosticable el fallo.
- La excepcion se vuelve a lanzar intacta: tragarsela le daria al planificador
  un codigo de salida cero para un trabajo que no hizo su trabajo.
- Las filas son historia: no se borran ni se reescriben tras cerrarse, mismo
  contrato que `audit.AuditEvent` (`RN-BIT-001`), sin actor porque estas
  ejecuciones no tienen a nadie detras.

### Contrato del log

El logger `siga.tasks` escribe `task.started`, `task.succeeded` y `task.failed`
con el nombre de la tarea, el identificador de la corrida y la duracion. Tiene
su propio handler con marca de tiempo y `pid` — sin eso no se distinguen dos
corridas de la misma tarea — y no propaga, para no duplicar cada linea en la
raiz.

Nivel configurable sin tocar codigo: `TASK_LOG_LEVEL`, que hereda de
`DJANGO_LOG_LEVEL` si no se define. `WARNING` calla inicio y fin y conserva solo
los fallos.

## Como se instrumenta una tarea

Un comando desatendido hereda de `MonitoredCommand` (`apps/common/management_base.py`),
implementa `run()` en vez de `handle()` y llena el `summary` que recibe en
`options`. No hay nada que recordar hacer: la instrumentacion no debe ser algo a
lo que cada tarea se apunte correctamente.

```python
from apps.common.management_base import MonitoredCommand


class Command(MonitoredCommand):
    def run(self, *args, **options):
        options["summary"]["revisados"] = 12
```

Codigo que no es un comando usa el gestor de contexto directamente:

```python
from apps.common.tasks import task_run

with task_run("nombre_estable") as summary:
    summary["procesados"] = 0
```

El nombre por defecto es el del modulo del comando: se mantiene estable aunque
la clase se renombre, y coincide con lo que un operador escribio en el `cron`.

## Tareas instrumentadas

| Tarea | Comando | Cadencia sugerida |
| --- | --- | --- |
| Integridad del almacenamiento documental | `check_document_storage_integrity` | Diaria, fuera de la jornada lectiva |

## Consulta

Requieren el permiso atomico `platform.monitor`, el del actor que nombra el
requerimiento (Administrador del sistema). Son de solo lectura: nada por HTTP
crea, edita ni borra una ejecucion.

| Endpoint | Que devuelve |
| --- | --- |
| `GET /api/v1/platform/task-runs/` | Historial de ejecuciones, mas reciente primero. Filtros `name` y `status` |
| `GET /api/v1/platform/task-health/` | Una fila por tarea conocida: ultima ejecucion, estado, duracion, total de corridas y de fallos |

El listado de tareas de `task-health` se deriva de las ejecuciones reales y no
de un registro de lo que *deberia* correr: un registro asi habria que mantenerlo
a mano y se quedaria viejo. Lo primero que un administrador necesita es la forma
de lo que efectivamente paso, y una tarea que nunca corrio se ve por su ausencia
en una lista corta.

El admin de Django expone `TaskRun` en modo solo lectura para inspeccion directa.

## Verificacion

| Escenario | Prueba |
| --- | --- |
| Camino feliz: fila cerrada con duracion, resumen y lineas de log | `backend/tests/unit/test_platform_task_monitoring.py::test_successful_task_is_recorded_with_its_summary` |
| Fallo: fila fallida con tipo y mensaje, resumen parcial, excepcion relanzada y log | `...::test_failing_task_is_recorded_reraised_and_logged` |
| La tarea que no corrio no deja fila | `...::test_a_task_that_never_ran_leaves_no_row` |
| Las ejecuciones son historia inmutable | `...::test_task_runs_are_history_and_cannot_be_deleted` |
| Resumen por tarea con el ultimo desenlace | `...::test_task_health_summary_reports_the_last_outcome_per_task` |
| Rechazo por autorizacion | `...::test_task_health_summary_denies_an_actor_without_the_permission` |
| Autenticacion y permiso en los dos endpoints | `backend/tests/api/test_platform_monitoring_api.py` |
| Nada se escribe por HTTP | `...::test_task_runs_cannot_be_written_over_http` |
| Un comando programado real deja registro, en exito y en fallo | `backend/tests/integration/test_platform_scheduled_tasks.py` |

Se corren con `make test-backend`.
