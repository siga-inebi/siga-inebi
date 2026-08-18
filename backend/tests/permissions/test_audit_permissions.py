"""
RF-BIT-001's security section: writes must keep respecting the domain's own
role/scope access control, and get audited either way -- allowed or denied.
"""

import pytest
from django.core.exceptions import PermissionDenied

from apps.audit.models import AuditEvent
from apps.identity.models import Role
from apps.identity.services import create_role
from tests.factories.identity import PermissionFactory, RoleAssignmentFactory, RoleFactory

pytestmark = [pytest.mark.permissions, pytest.mark.django_db]


def test_authorized_write_is_audited():
    permission = PermissionFactory(codename="role_assign")
    assignment = RoleAssignmentFactory(role=RoleFactory(permissions=[permission]))

    role = create_role(actor=assignment.user, name="Coordinador", slug="coordinador")

    assert Role.objects.filter(pk=role.pk).exists()
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "identity.role.created"
    assert event.actor_id == assignment.user.id
    assert event.context["result"] == "success"


def test_denied_write_is_still_audited():
    assignment = RoleAssignmentFactory(role=RoleFactory(permissions=[]))

    with pytest.raises(PermissionDenied):
        create_role(actor=assignment.user, name="Coordinador", slug="coordinador")

    event = AuditEvent.objects.latest("created_at")
    assert event.action == "identity.role.create_denied"
    assert event.context["result"] == "denied"
    assert not Role.objects.filter(slug="coordinador").exists()
