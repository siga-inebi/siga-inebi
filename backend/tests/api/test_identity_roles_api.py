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


def _role_administrator(client):
    actor = UserFactory()
    permission = PermissionFactory(codename="role_assign")
    RoleAssignmentFactory(user=actor, role=RoleFactory(permissions=[permission]))
    client.force_login(actor)
    return actor


def test_role_endpoints_require_authentication(client):
    response = client.get(reverse("identity-role-list-create"))

    assert response.status_code in (401, 403)


def test_authorized_administrator_creates_and_updates_role_composition(client):
    actor = _role_administrator(client)
    created = client.post(
        reverse("identity-role-list-create"),
        {
            "name": "Attendance Operator",
            "slug": "attendance-operator-custom",
            "permissions": ["attendance.record_entry"],
        },
        content_type="application/json",
    )

    assert created.status_code == 201
    role_id = created.json()["public_id"]
    updated = client.patch(
        reverse("identity-role-detail", args=[role_id]),
        {"permissions": ["attendance.record_entry", "attendance.record_exit"]},
        content_type="application/json",
    )

    assert updated.status_code == 200
    assert updated.json()["permissions"] == [
        "attendance.record_entry",
        "attendance.record_exit",
    ]
    event = AuditEvent.objects.get(action="identity.role.updated")
    assert event.actor == actor


def test_account_can_receive_multiple_roles_and_revocation_applies_immediately(client):
    _role_administrator(client)
    target = UserFactory()
    first = RoleFactory(permissions=[PermissionFactory(codename="student_view_basic")])
    second = RoleFactory(permissions=[PermissionFactory(codename="audit_read")])

    first_response = client.post(
        reverse("identity-role-assignment-create", args=[target.pk]),
        {"role": str(first.public_id)},
        content_type="application/json",
    )
    second_response = client.post(
        reverse("identity-role-assignment-create", args=[target.pk]),
        {"role": str(second.public_id)},
        content_type="application/json",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert target.has_atomic_permission("student_view_basic") is True
    assert target.has_atomic_permission("audit_read") is True

    revoked = client.delete(
        reverse("identity-role-assignment-revoke", args=[second_response.json()["public_id"]])
    )

    assert revoked.status_code == 200
    assert target.has_atomic_permission("student_view_basic") is True
    assert target.has_atomic_permission("audit_read") is False
