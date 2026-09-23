"""
Registro y monitoreo de tareas en segundo plano y programadas (RNF-OPE-001).

Una tarea programada falla en silencio por omision: el cron la lanza, el error
se va a la salida estandar de un contenedor que nadie mira, y nadie se entera
hasta que alguien nota el efecto semanas despues. Este modulo cierra esa puerta
con dos registros complementarios:

- una fila ``TaskRun`` por ejecucion, que sobrevive al proceso y hace visible
  tambien la ejecucion que NO ocurrio (no hay fila);
- una linea de log estructurada por inicio, fin y fallo, para quien este mirando
  la salida en vivo o la tenga recolectada.

Las dos se escriben desde un unico punto, ``task_run``, para que no puedan
contarse historias distintas. Los fallos nunca se tragan: se registran y se
vuelven a lanzar, porque el codigo de salida es lo que hace que el cron o el
orquestador se den por enterados.

ADR-0009 difiere el proceso trabajador, asi que hoy las tareas que pasan por
aqui son comandos de gestion invocados por cron. El contrato esta escrito
pensando en el worker: cuando exista, instrumentar sus trabajos es usar el mismo
gestor de contexto.
"""

import logging
import os
import socket
import time
from contextlib import contextmanager

from django.utils import timezone

from apps.common.models import TaskRun

logger = logging.getLogger("siga.tasks")

# Un traceback completo no cabe ni sirve en una columna que se lee en una
# tabla; el mensaje identifica el fallo y el log conserva el detalle.
MAX_ERROR_MESSAGE_LENGTH = 2000


def _host():
    try:
        return socket.gethostname()[:255]
    except OSError:
        # Un contenedor sin resolucion de nombres no es motivo para perder el
        # registro de la ejecucion.
        return ""


def start_task_run(*, name):
    """Open a run and log its start. Returns the persisted ``TaskRun``."""
    run = TaskRun.objects.create(
        name=name,
        status=TaskRun.Status.RUNNING,
        started_at=timezone.now(),
        host=_host(),
        process_id=os.getpid(),
    )
    logger.info("task.started name=%s run_id=%s", name, run.public_id)
    return run


def _finish(run, *, status, summary, error=None, monotonic_start):
    run.status = status
    run.finished_at = timezone.now()
    run.duration_ms = int((time.monotonic() - monotonic_start) * 1000)
    run.summary = summary or {}
    if error is not None:
        run.error_type = type(error).__name__[:150]
        run.error_message = str(error)[:MAX_ERROR_MESSAGE_LENGTH]
    run.save(
        update_fields=[
            "status",
            "finished_at",
            "duration_ms",
            "summary",
            "error_type",
            "error_message",
            "updated_at",
        ]
    )
    return run


@contextmanager
def task_run(name, *, summary=None):
    """
    Record one execution of the named task.

    The caller receives a mutable ``dict``; whatever it leaves there is stored
    as the run's summary. A mutable object rather than a return value because
    a failing task has no return value, and its partial counters are exactly
    what makes the failure diagnosable.

    The exception is logged with its traceback, recorded on the run and then
    re-raised untouched: swallowing it would give the scheduler a zero exit
    code for a job that did not do its work.
    """
    run = start_task_run(name=name)
    collected = summary if summary is not None else {}
    monotonic_start = time.monotonic()

    try:
        yield collected
    except BaseException as exc:  # noqa: BLE001 - re-raised below, nothing swallowed
        _finish(
            run,
            status=TaskRun.Status.FAILED,
            summary=collected,
            error=exc,
            monotonic_start=monotonic_start,
        )
        logger.exception(
            "task.failed name=%s run_id=%s duration_ms=%s", name, run.public_id, run.duration_ms
        )
        raise

    _finish(
        run,
        status=TaskRun.Status.SUCCEEDED,
        summary=collected,
        monotonic_start=monotonic_start,
    )
    logger.info(
        "task.succeeded name=%s run_id=%s duration_ms=%s summary=%s",
        name,
        run.public_id,
        run.duration_ms,
        collected,
    )
    return
