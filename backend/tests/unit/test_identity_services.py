import pytest
from django.core.exceptions import PermissionDenied

from apps.audit.models import AuditEvent
from apps.identity.services import list_atomic_permissions
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
