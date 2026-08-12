import pytest
from django.core.exceptions import PermissionDenied

from apps.audit.models import AuditEvent
from apps.identity.services import (
    create_role,
    list_atomic_permissions,
    revoke_role_assignment,
    update_role,
)
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)


@pytest.mark.django_db
def test_permission_catalog_requires_administrative_permission():
    actor = UserFactory()

    with pytest.raises(PermissionDenied):
        list_atomic_permissions(actor=actor)

    event = AuditEvent.objects.get(action="identity.permission_catalog.read_denied")
    assert event.actor == actor
    assert event.context["reason"] == "missing_permission"


@pytest.mark.django_db
def test_permission_catalog_returns_only_registered_atomic_permissions():
    actor = UserFactory()
    role_assign = PermissionFactory(codename="role_assign")
    RoleAssignmentFactory(user=actor, role=RoleFactory(permissions=[role_assign]))
    PermissionFactory(codename="unregistered_permission")

    permissions = list(list_atomic_permissions(actor=actor))

    codenames = {permission.codename for permission in permissions}
    assert "role_assign" in codenames
    assert "attendance_record_entry" in codenames
    assert "attendance_record_exit" in codenames
    assert "attendance_declared_close" in codenames
    assert "unregistered_permission" not in codenames
    event = AuditEvent.objects.get(action="identity.permission_catalog.read")
    assert event.context["permission_count"] == len(permissions)


@pytest.mark.django_db
def test_role_composition_change_applies_to_assigned_accounts_and_is_audited():
    actor = UserFactory(is_superuser=True)
    target = UserFactory()
    role = create_role(
        actor=actor,
        name="Attendance Operator",
        slug="attendance-operator-custom",
        permission_codenames=["attendance_record_entry"],
    )
    assignment = RoleAssignmentFactory(user=target, role=role)

    assert target.has_atomic_permission("attendance_record_exit") is False

    update_role(
        actor=actor,
        role=role,
        permission_codenames=["attendance_record_entry", "attendance_record_exit"],
    )

    assert target.has_atomic_permission("attendance_record_exit") is True
    event = AuditEvent.objects.get(action="identity.role.updated")
    assert event.actor == actor
    assert event.context["before"]["permissions"] == ["attendance_record_entry"]
    assert event.context["after"]["permissions"] == [
        "attendance_record_entry",
        "attendance_record_exit",
    ]
    assert assignment.user_id == target.pk


@pytest.mark.django_db
def test_revoked_role_is_denied_on_next_permission_evaluation():
    actor = UserFactory(is_superuser=True)
    target = UserFactory()
    permission = PermissionFactory(codename="audit_read")
    assignment = RoleAssignmentFactory(
        user=target,
        role=RoleFactory(permissions=[permission]),
    )

    assert target.has_atomic_permission("audit_read") is True

    revoke_role_assignment(actor=actor, assignment=assignment)

    assert target.has_atomic_permission("audit_read") is False
    assert AuditEvent.objects.filter(
        action="identity.role_assignment.revoked",
        actor=actor,
    ).exists()
