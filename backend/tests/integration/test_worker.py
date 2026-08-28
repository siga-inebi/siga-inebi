"""
RNF-REN-004 — el trabajador opera con concurrencia de uno y ventana horaria.

Escenarios derivados del criterio de aceptacion (el requerimiento no trae
escenarios en la fuente, y quedan anotados en el issue #288):

1. Camino feliz: dentro de la ventana, el trabajador toma un trabajo de la
   cola de RNF-REN-003 y lo ejecuta.
2. Fuera de la ventana no toca la cola, aunque haya trabajo pendiente.
3. La ventana normal cruza la medianoche, porque las horas fuera de la jornada
   son las de despues del cierre y las de antes de la entrada.
4. Una ventana con inicio y fin iguales drena todo el dia.
5. La ventana se lee en la hora local del establecimiento (RNF-LOC-001), no en
   la del servidor.
6. Un segundo trabajador no toma trabajos mientras el primero tiene el
   bloqueo: la concurrencia es de uno, verificada en la base de datos.
7. El bloqueo se libera al terminar, para que el siguiente arranque lo tome.
8. Una ventana mal escrita falla al arrancar y lo dice, en lugar de drenar en
   un horario que nadie configuro.

No hay escenario de rechazo por autorizacion: el trabajador no expone
endpoint y el issue declara "sin requisitos de autorizacion adicionales a los
del dominio"; quien lo ejecuta ya tiene el host.
"""

import threading
from datetime import time, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import override_settings
from django.utils import timezone

from apps.common import jobs
from apps.common.models import Job
from apps.common.worker import single_worker_lock, window_is_open

pytestmark = [pytest.mark.integration, pytest.mark.postgres, pytest.mark.django_db]

ALWAYS_OPEN = {"WORKER_WINDOW_START": "00:00", "WORKER_WINDOW_END": "00:00"}
CALLS = []

TEST_LOCK_ID = 990001


@pytest.fixture(autouse=True)
def _registered_task():
    original = dict(jobs._REGISTRY)
    CALLS.clear()

    @jobs.task("tests.worker")
    def _record(**payload):
        CALLS.append(payload)

    yield
    jobs._REGISTRY.clear()
    jobs._REGISTRY.update(original)


def run_worker(**settings_overrides):
    output = StringIO()
    with override_settings(WORKER_CONCURRENCY_LOCK_ID=TEST_LOCK_ID, **settings_overrides):
        call_command("run_worker", "--once", stdout=output)
    return output.getvalue()


@override_settings(**ALWAYS_OPEN)
def test_inside_the_window_the_worker_runs_a_queued_job():
    jobs.enqueue(task="tests.worker", payload={"value": 3})

    run_worker(**ALWAYS_OPEN)

    assert CALLS == [{"value": 3}]
    assert Job.objects.get().status == Job.Status.SUCCEEDED


def test_outside_the_window_the_worker_leaves_the_queue_alone():
    """
    The point of the window: while the porton is scanning, a confirmation has
    a 2 s budget (RNF-REN-001) and the worker must not spend any of it.
    """
    jobs.enqueue(task="tests.worker", payload={"value": 3})
    now = timezone.localtime()
    closed_start = (now + timedelta(hours=2)).time().replace(second=0, microsecond=0)
    closed_end = (now + timedelta(hours=4)).time().replace(second=0, microsecond=0)

    output = run_worker(
        WORKER_WINDOW_START=closed_start.strftime("%H:%M"),
        WORKER_WINDOW_END=closed_end.strftime("%H:%M"),
    )

    assert CALLS == []
    assert Job.objects.get().status == Job.Status.QUEUED
    assert "Fuera de la ventana horaria" in output


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (time(23, 30), True),
        (time(3, 0), True),
        (time(19, 0), True),
        (time(5, 0), False),
        (time(7, 25), False),
        (time(12, 0), False),
        (time(18, 59), False),
    ],
)
def test_the_window_crosses_midnight(now, expected):
    assert window_is_open(now, start=time(19, 0), end=time(5, 0)) is expected


@pytest.mark.parametrize("now", [time(0, 0), time(9, 15), time(23, 59)])
def test_a_window_with_equal_bounds_drains_all_day(now):
    assert window_is_open(now, start=time(6, 0), end=time(6, 0)) is True


def test_the_window_is_read_in_the_establishment_clock():
    """
    RNF-LOC-001: the school day is written in local time, so a host whose own
    clock runs on UTC must not drain on UTC hours.

    The window here is the one hour that contains *this instant in Guatemala*
    and, because the offset is six hours, cannot contain the same instant read
    as UTC. The same queue and the same window therefore drain under one
    setting and stay untouched under the other, which is exactly the mistake
    a server in UTC would make.
    """
    jobs.enqueue(task="tests.worker", payload={"value": 3})
    with override_settings(TIME_ZONE="America/Guatemala"):
        local_hour = timezone.localtime().hour
    window = {
        "WORKER_WINDOW_START": f"{local_hour:02d}:00",
        "WORKER_WINDOW_END": f"{(local_hour + 1) % 24:02d}:00",
    }

    with override_settings(TIME_ZONE="UTC"):
        run_worker(**window)
    assert CALLS == []

    with override_settings(TIME_ZONE="America/Guatemala"):
        run_worker(**window)
    assert CALLS == [{"value": 3}]


@pytest.mark.django_db(transaction=True)
@override_settings(**ALWAYS_OPEN)
def test_a_second_worker_does_not_take_jobs_while_the_first_holds_the_lock():
    jobs.enqueue(task="tests.worker", payload={"value": 3})
    holding = threading.Event()
    release = threading.Event()

    def hold_the_lock():
        try:
            with single_worker_lock(TEST_LOCK_ID) as acquired:
                assert acquired is True
                holding.set()
                release.wait(timeout=5)
        finally:
            connection.close()

    first = threading.Thread(target=hold_the_lock)
    first.start()
    assert holding.wait(timeout=5), "the first worker never acquired the lock"

    output = run_worker(**ALWAYS_OPEN)

    release.set()
    first.join(timeout=5)

    assert CALLS == []
    assert Job.objects.get().status == Job.Status.QUEUED
    assert "Ya hay un proceso trabajador en ejecucion" in output


@pytest.mark.django_db(transaction=True)
@override_settings(**ALWAYS_OPEN)
def test_the_lock_is_released_so_the_next_start_can_take_it():
    jobs.enqueue(task="tests.worker", payload={"value": 3})

    run_worker(**ALWAYS_OPEN)
    jobs.enqueue(task="tests.worker", payload={"value": 4})
    run_worker(**ALWAYS_OPEN)

    assert CALLS == [{"value": 3}, {"value": 4}]


def test_a_malformed_window_stops_the_worker_at_startup():
    with pytest.raises(CommandError, match="WORKER_WINDOW_START"):
        run_worker(WORKER_WINDOW_START="siete de la manana", WORKER_WINDOW_END="05:00")
