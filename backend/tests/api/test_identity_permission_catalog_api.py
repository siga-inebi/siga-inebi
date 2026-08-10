import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_permission_catalog_requires_authentication(client):
    response = client.get(reverse("identity-permission-list"))

    assert response.status_code in (401, 403)


@pytest.mark.security
def test_permission_catalog_denies_user_without_administrative_permission(client):
    actor = UserFactory()
    client.force_login(actor)

    response = client.get(reverse("identity-permission-list"))

    assert response.status_code == 403
    assert AuditEvent.objects.filter(
        actor=actor,
        action="identity.permission_catalog.read_denied",
    ).exists()


def test_administrator_can_consult_distinct_attendance_permissions(client):
    actor = UserFactory()
    role_assign = PermissionFactory(codename="role_assign")
    RoleAssignmentFactory(user=actor, role=RoleFactory(permissions=[role_assign]))
    client.force_login(actor)

    response = client.get(reverse("identity-permission-list"))

    assert response.status_code == 200
    codes = {item["code"] for item in response.json()["results"]}
    assert {
        "attendance.record_entry",
        "attendance.record_exit",
        "attendance.declared_close",
    } <= codes
