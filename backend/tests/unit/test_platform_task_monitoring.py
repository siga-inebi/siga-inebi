"""
RNF-OPE-001: registro de errores y monitoreo de tareas en segundo plano.

Escenarios derivados del criterio (la fuente no trae ninguno):

1. Camino feliz: una tarea que termina bien deja una fila cerrada con su
   duracion y su resumen, mas una linea de log.
2. Fallo: una tarea que revienta deja la fila marcada como fallida con el tipo
   y el mensaje del error, la excepcion se vuelve a lanzar y el error queda en
   el log.
3. Rechazo por autorizacion: leer el monitoreo sin `platform.monitor` se
   deniega.
"""

import logging

import pytest

from apps.common.exceptions import AuthorizationError
from apps.common.models import TaskRun
from apps.common.services import task_health_summary
from apps.common.tasks import task_run
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def task_logs(caplog):
    """
    Capture the ``siga.tasks`` logger.

    ``caplog`` alone sees nothing here: the logger is configured with
    ``propagate = False`` so its lines do not get duplicated into the root
    handler, and ``caplog`` listens on the root. Attaching its handler
    directly keeps the production configuration under test instead of
    loosening it for the tests' convenience.
    """
    logger = logging.getLogger("siga.tasks")
    previous_level = logger.level
    logger.addHandler(caplog.handler)
    logger.setLevel(logging.INFO)
    try:
        yield caplog
    finally:
        logger.removeHandler(caplog.handler)
        logger.setLevel(previous_level)


def _monitor(user):
    RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[PermissionFactory(codename="platform_monitor")]),
    )
    return user


def test_successful_task_is_recorded_with_its_summary(task_logs):
    with task_run("nightly_check") as summary:
        summary["checked"] = 12

    run = TaskRun.objects.get(name="nightly_check")

    assert run.status == TaskRun.Status.SUCCEEDED
    assert run.summary == {"checked": 12}
    assert run.finished_at is not None
    assert run.duration_ms is not None
    assert run.host
    assert run.process_id
    assert "task.started" in task_logs.text
    assert "task.succeeded" in task_logs.text


def test_failing_task_is_recorded_reraised_and_logged(task_logs):
    with pytest.raises(ValueError, match="sin espacio"), task_run("nightly_check") as summary:
        summary["checked"] = 3
        raise ValueError("sin espacio en disco")

    run = TaskRun.objects.get(name="nightly_check")

    assert run.status == TaskRun.Status.FAILED
    assert run.error_type == "ValueError"
    assert run.error_message == "sin espacio en disco"
    # El resumen parcial se conserva: es lo que hace diagnosticable el fallo.
    assert run.summary == {"checked": 3}
    assert run.finished_at is not None
    assert "task.failed" in task_logs.text


def test_a_task_that_never_ran_leaves_no_row():
    """La ausencia ES la senal: no hay forma de confundirla con un exito."""
    with task_run("nightly_check"):
        pass

    assert TaskRun.objects.filter(name="nightly_check").count() == 1
    assert not TaskRun.objects.filter(name="weekly_backup").exists()


def test_task_runs_are_history_and_cannot_be_deleted():
    with task_run("nightly_check"):
        pass

    run = TaskRun.objects.get(name="nightly_check")

    with pytest.raises(RuntimeError, match="cannot be deleted"):
        run.delete()


def test_task_health_summary_reports_the_last_outcome_per_task():
    with task_run("nightly_check") as summary:
        summary["checked"] = 1
    with pytest.raises(ValueError, match="fallo"), task_run("nightly_check"):
        raise ValueError("fallo")

    [health] = task_health_summary(actor=_monitor(UserFactory()))

    assert health["name"] == "nightly_check"
    assert health["total_runs"] == 2
    assert health["failed_runs"] == 1
    assert health["last_status"] == TaskRun.Status.FAILED
    assert health["last_error_message"] == "fallo"


def test_task_health_summary_denies_an_actor_without_the_permission():
    with pytest.raises(AuthorizationError):
        task_health_summary(actor=UserFactory())
