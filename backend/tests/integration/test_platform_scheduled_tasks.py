"""
RNF-OPE-001: un comando programado deja registro de su ejecucion.

Se prueba contra el unico comando que hoy corre desatendido desde cron, la
verificacion de integridad del almacenamiento documental, porque lo que importa
no es el envoltorio en abstracto sino que una tarea real lo use.
"""

import pytest
from django.core.management import call_command

from apps.common.models import TaskRun

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_scheduled_integrity_check_records_a_successful_run():
    call_command("check_document_storage_integrity")

    run = TaskRun.objects.get(name="check_document_storage_integrity")

    assert run.status == TaskRun.Status.SUCCEEDED
    assert run.summary["total_checked"] == 0
    assert run.summary["corrupted"] == 0
    assert run.duration_ms is not None


def test_scheduled_integrity_check_records_a_failed_run_and_keeps_the_exit_code():
    with pytest.raises(SystemExit):
        call_command("check_document_storage_integrity", institution_id="no-existe")

    run = TaskRun.objects.get(name="check_document_storage_integrity")

    assert run.status == TaskRun.Status.FAILED
    assert run.error_type == "SystemExit"
    assert "no-existe" in run.error_message
