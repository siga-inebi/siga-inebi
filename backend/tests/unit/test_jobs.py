"""
RNF-REN-003 — heavy work is enqueued instead of run inside the request.

Escenarios derivados del criterio de aceptacion (el requerimiento no trae
escenarios en la fuente, y quedan anotados en el issue #287):

1. Camino feliz: encolar registra el trabajo y devuelve sin ejecutar nada, de
   modo que el tiempo de la peticion deja de depender del tamano del trabajo.
2. El trabajo encolado se ejecuta despues y produce el mismo efecto.
3. Un nombre de tarea que no existe se rechaza al encolar, no en el worker.
4. Un fallo transitorio no pierde el trabajo: vuelve a la cola con espera.
5. Agotados los intentos, el trabajo queda fallido y nadie lo vuelve a tomar.
6. Un trabajo con fecha de disponibilidad futura todavia no se toma.
7. La transaccion que no confirma no deja trabajo huerfano.
8. Dos tomadores simultaneos nunca se llevan el mismo trabajo.

No hay escenario de rechazo por autorizacion: la cola no expone endpoint y el
issue declara "sin requisitos de autorizacion adicionales a los del dominio".
El permiso lo sigue verificando el servicio que encola, antes de encolar.
"""

import threading
from datetime import timedelta

import pytest
from django.db import connection, transaction
from django.utils import timezone

from apps.common import jobs
from apps.common.models import Job

pytestmark = [pytest.mark.unit, pytest.mark.postgres, pytest.mark.django_db]

CALLS = []


@pytest.fixture(autouse=True)
def _isolated_registry():
    """Each test gets the real registry back untouched."""
    original = dict(jobs._REGISTRY)
    CALLS.clear()
    yield
    jobs._REGISTRY.clear()
    jobs._REGISTRY.update(original)


@pytest.fixture
def recording_task():
    @jobs.task("tests.record")
    def _record(**payload):
        CALLS.append(payload)

    return _record


def test_enqueue_records_the_work_without_running_it(recording_task):
    job = jobs.enqueue(task="tests.record", payload={"value": 7})

    assert CALLS == []
    assert job.status == Job.Status.QUEUED
    assert job.payload == {"value": 7}
    assert job.attempts == 0


def test_claimed_job_runs_the_handler_with_its_payload(recording_task):
    jobs.enqueue(task="tests.record", payload={"value": 7})

    job = jobs.run_job(jobs.claim_next_job())

    assert CALLS == [{"value": 7}]
    assert job.status == Job.Status.SUCCEEDED
    assert job.finished_at is not None


def test_enqueueing_an_unknown_task_fails_in_the_request_that_wrote_it():
    with pytest.raises(jobs.TaskNotRegistered):
        jobs.enqueue(task="tests.does-not-exist")

    assert Job.objects.count() == 0


def test_transient_failure_returns_the_job_to_the_queue_with_a_backoff():
    @jobs.task("tests.flaky")
    def _flaky():
        raise ValueError("la base de datos estaba reiniciando")

    before = timezone.now()
    jobs.enqueue(task="tests.flaky")
    job = jobs.run_job(jobs.claim_next_job())

    assert job.status == Job.Status.QUEUED
    assert job.attempts == 1
    assert job.available_at >= before + jobs.RETRY_BACKOFF
    assert "ValueError" in job.last_error
    # Still invisible right now: a retry that runs in the same instant spends
    # the budget without giving the transient cause time to clear.
    assert jobs.claim_next_job() is None


def test_job_stays_failed_once_it_runs_out_of_attempts():
    @jobs.task("tests.broken")
    def _broken():
        raise ValueError("no se puede leer la plantilla")

    jobs.enqueue(task="tests.broken", max_attempts=1)
    job = jobs.run_job(jobs.claim_next_job())

    assert job.status == Job.Status.FAILED
    assert job.finished_at is not None
    assert jobs.claim_next_job(now=timezone.now() + timedelta(days=1)) is None


def test_a_job_scheduled_for_later_is_not_claimed_yet(recording_task):
    later = timezone.now() + timedelta(hours=2)
    jobs.enqueue(task="tests.record", available_at=later)

    assert jobs.claim_next_job() is None
    assert jobs.claim_next_job(now=later) is not None


def test_a_rolled_back_transaction_leaves_no_orphan_job(recording_task):
    with pytest.raises(RuntimeError), transaction.atomic():
        jobs.enqueue(task="tests.record")
        raise RuntimeError("el servicio de dominio fallo despues de encolar")

    assert Job.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_two_simultaneous_claimers_never_take_the_same_job(recording_task):
    """
    The guarantee that lets RNF-REN-004's concurrency setting be an
    operational choice rather than a correctness requirement: even if a second
    worker is started by mistake, ``FOR UPDATE SKIP LOCKED`` hands it the next
    row or nothing at all, never a job already running.
    """
    jobs.enqueue(task="tests.record", payload={"value": 1})
    claimed = []
    holding = threading.Event()
    release = threading.Event()

    def claim_and_hold():
        try:
            with transaction.atomic():
                job = (
                    Job.objects.select_for_update(skip_locked=True)
                    .filter(status=Job.Status.QUEUED)
                    .first()
                )
                claimed.append(job)
                holding.set()
                release.wait(timeout=5)
        finally:
            connection.close()

    first = threading.Thread(target=claim_and_hold)
    first.start()
    assert holding.wait(timeout=5), "the first claimer never acquired its row"

    second = jobs.claim_next_job()
    release.set()
    first.join(timeout=5)

    assert claimed[0] is not None
    assert second is None
