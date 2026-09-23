"""RNF-OPE-001: superficie de lectura del monitoreo operativo."""

import pytest
from django.urls import reverse

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


@pytest.mark.parametrize("route", ["platform-task-run-list", "platform-task-health"])
def test_monitoring_endpoints_require_authentication(client, route):
    assert client.get(reverse(route)).status_code in {401, 403}


@pytest.mark.parametrize("route", ["platform-task-run-list", "platform-task-health"])
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
