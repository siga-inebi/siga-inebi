"""RNF-OPE-001: superficie de lectura del monitoreo operativo."""

import json
from datetime import timedelta

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.common.models import TaskRun
from apps.common.tasks import task_run
from tests.factories.identity import PermissionFactory, RoleAssignmentFactory, RoleFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _grant_monitor(user):
    return RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[PermissionFactory(codename="platform_monitor")]),
    )


def _items(response):
    return response.json()["results"]


MONITORED_ROUTES = [
    "platform-task-run-list",
    "platform-task-health",
    "platform-backup-health",
]


@pytest.mark.parametrize("route", MONITORED_ROUTES)
def test_monitoring_endpoints_require_authentication(client, route):
    assert client.get(reverse(route)).status_code in {401, 403}


@pytest.mark.parametrize("route", MONITORED_ROUTES)
def test_monitoring_endpoints_deny_an_actor_without_the_permission(auth_client, route):
    assert auth_client.get(reverse(route)).status_code == 403


def test_task_run_list_shows_the_recorded_executions(auth_client):
    _grant_monitor(auth_client.user)
    with task_run("nightly_check") as summary:
        summary["checked"] = 4

    response = auth_client.get(reverse("platform-task-run-list"))

    assert response.status_code == 200
    [item] = _items(response)
    assert item["name"] == "nightly_check"
    assert item["status"] == TaskRun.Status.SUCCEEDED
    assert item["summary"] == {"checked": 4}


def test_task_run_list_filters_by_name_and_status(auth_client):
    _grant_monitor(auth_client.user)
    with task_run("nightly_check"):
        pass
    with pytest.raises(ValueError, match="fallo"), task_run("weekly_backup"):
        raise ValueError("fallo")

    failed = auth_client.get(reverse("platform-task-run-list"), {"status": TaskRun.Status.FAILED})

    assert [item["name"] for item in _items(failed)] == ["weekly_backup"]

    by_name = auth_client.get(reverse("platform-task-run-list"), {"name": "nightly_check"})

    assert [item["name"] for item in _items(by_name)] == ["nightly_check"]


def test_task_health_reports_one_row_per_task(auth_client):
    _grant_monitor(auth_client.user)
    with task_run("nightly_check"):
        pass
    with pytest.raises(ValueError, match="fallo"), task_run("nightly_check"):
        raise ValueError("fallo")

    response = auth_client.get(reverse("platform-task-health"))

    assert response.status_code == 200
    [item] = _items(response)
    assert item["name"] == "nightly_check"
    assert item["total_runs"] == 2
    assert item["failed_runs"] == 1
    assert item["last_status"] == TaskRun.Status.FAILED


def test_task_runs_cannot_be_written_over_http(auth_client):
    _grant_monitor(auth_client.user)

    response = auth_client.post(
        reverse("platform-task-run-list"),
        {"name": "inventada"},
        content_type="application/json",
    )

    assert response.status_code == 405
    assert not TaskRun.objects.exists()


def test_backup_health_reports_each_stack_separately(auth_client, tmp_path):
    """RNF-RES-001/002: nunca agregadas, porque las pilas son independientes."""
    _grant_monitor(auth_client.user)
    database_dir = tmp_path / "database"
    database_dir.mkdir()
    artifact = database_dir / "siga-db-20260101T000000Z.dump"
    artifact.write_bytes(b"dump")
    (database_dir / "siga-db-20260101T000000Z.manifest.json").write_text(
        json.dumps(
            {
                "kind": "database",
                "artifact": artifact.name,
                "created_at": (timezone.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "size_bytes": 4,
                "sha256": "0" * 64,
            }
        )
    )

    with override_settings(
        DATABASE_BACKUP_DIR=str(database_dir),
        FILES_BACKUP_DIR=str(tmp_path / "files"),
        RECOVERY_POINT_OBJECTIVE_HOURS=24,
    ):
        response = auth_client.get(reverse("platform-backup-health"))

    assert response.status_code == 200
    health = {item["stack"]: item for item in _items(response)}
    assert health["database"]["meets_rpo"] is True
    assert health["files"]["meets_rpo"] is False
    assert health["files"]["backup_count"] == 0
