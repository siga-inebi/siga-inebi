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


def test_direct_role_operation_without_permission_is_denied_and_audited(client):
    actor = UserFactory()
    client.force_login(actor)

    response = client.post(
        reverse("identity-role-list-create"),
        {"name": "Denied", "slug": "denied", "permissions": []},
        content_type="application/json",
    )

    assert response.status_code == 403
    assert AuditEvent.objects.filter(
        actor=actor,
        action="identity.authorization.denied",
    ).exists()


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
        {"role": str(first.public_id), "scope": {"module_key": "identity"}},
        content_type="application/json",
    )
    second_response = client.post(
        reverse("identity-role-assignment-create", args=[target.pk]),
        {"role": str(second.public_id), "scope": {"module_key": "identity"}},
        content_type="application/json",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert (
        target.has_scoped_permission("student_view_basic", scope={"module_key": "identity"}) is True
    )
    assert target.has_scoped_permission("audit_read", scope={"module_key": "identity"}) is True

    revoked = client.delete(
        reverse("identity-role-assignment-revoke", args=[second_response.json()["public_id"]])
    )

    assert revoked.status_code == 200
    assert (
        target.has_scoped_permission("student_view_basic", scope={"module_key": "identity"}) is True
    )
    assert target.has_scoped_permission("audit_read", scope={"module_key": "identity"}) is False
