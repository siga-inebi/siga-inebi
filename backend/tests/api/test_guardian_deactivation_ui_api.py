"""#632 G3: authorized logical deactivation, atomic audit and retained history."""

import importlib
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.students.services import deactivate_guardian
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.students import GuardianFactory, StudentGuardianRelationFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def grant(user, *, module="students"):
    assignment = RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[PermissionFactory(codename="guardian_deactivate")]),
        identity_scope=False,
    )
    if module:
        ScopeGrantFactory(assignment=assignment, module_key=module)
    return assignment


def test_deactivation_preserves_person_account_relations_and_revokes_derived_scope(auth_client):
    from apps.identity.scopes import guardian_student_queryset

    guardian = GuardianFactory()
    account = UserFactory(person=guardian.person)
    relation = StudentGuardianRelationFactory(guardian=guardian, is_primary=True)
    assert guardian_student_queryset(user=account).filter(pk=relation.student_id).exists()
    grant(auth_client.user)
    response = auth_client.delete(reverse("guardian-detail", args=[guardian.pk]))
    assert response.status_code == 204 and response.content == b""
    guardian.refresh_from_db()
    assert not guardian.is_active
    for retained in (guardian.person, account, relation, relation.student):
        retained.refresh_from_db()
        assert retained.is_active
    assert relation.ends_at is None and relation.is_primary
    assert account.person_id == guardian.person_id
    account = type(account).objects.get(pk=account.pk)
    assert not guardian_student_queryset(user=account).exists()
    other_role = RoleAssignmentFactory(
        user=account,
        role=RoleFactory(permissions=[PermissionFactory(codename="student_view_basic")]),
        identity_scope=False,
    )
    ScopeGrantFactory(assignment=other_role, student=relation.student)
    assert account.has_scoped_permission("student_view_basic", scope={"student": relation.student})
    event = AuditEvent.objects.get(action="students.guardian.deactivated")
    assert event.actor == auth_client.user
    assert event.resource_identifier == str(guardian.pk)
    assert event.context["is_active"] == {"old": True, "new": False}
    detail = auth_client.get(reverse("guardian-detail", args=[guardian.pk])).json()
    assert detail["is_active"] is False and detail["actions"] == {"deactivate": False}
    assert auth_client.get(reverse("guardian-list")).json()["count"] == 0
    assert (
        auth_client.get(reverse("guardian-list"), {"include_inactive": "true"}).json()["count"] == 1
    )


@pytest.mark.parametrize("scope", [None, "teachers", "identity"])
def test_permission_without_students_scope_is_denied_and_audited(auth_client, scope):
    guardian = GuardianFactory()
    grant(auth_client.user, module=scope)
    assert auth_client.delete(reverse("guardian-detail", args=[guardian.pk])).status_code == 403
    guardian.refresh_from_db()
    assert guardian.is_active
    assert AuditEvent.objects.filter(
        actor=auth_client.user, action="identity.authorization.denied", resource="Guardian"
    ).exists()
    assert not AuditEvent.objects.filter(action="students.guardian.deactivated").exists()


def test_anonymous_and_session_without_permission_cannot_deactivate(auth_client):
    guardian = GuardianFactory()
    url = reverse("guardian-detail", args=[guardian.pk])
    assert Client().delete(url).status_code == 403
    assert auth_client.delete(url).status_code == 403
    assert auth_client.get(url).json()["actions"] == {"deactivate": False}


def test_capabilities_do_not_audit_unattempted_writes_and_delete_revalidates(auth_client):
    guardian = GuardianFactory()
    url = reverse("guardian-detail", args=[guardian.pk])
    assert auth_client.get(url).json()["actions"] == {"deactivate": False}
    assignment = grant(auth_client.user)
    assert auth_client.get(url).json()["actions"] == {"deactivate": True}
    assert not AuditEvent.objects.filter(action="identity.authorization.denied").exists()
    assignment.ends_at = timezone.now() - timezone.timedelta(seconds=1)
    assignment.save(update_fields=["ends_at"])
    assert auth_client.delete(url).status_code == 403
    guardian.refresh_from_db()
    assert guardian.is_active


def test_expired_scope_and_inactive_role_cannot_deactivate(auth_client):
    guardian = GuardianFactory()
    assignment = grant(auth_client.user)
    assignment.scope_grants.update(ends_at=timezone.now() - timezone.timedelta(seconds=1))
    assert auth_client.delete(reverse("guardian-detail", args=[guardian.pk])).status_code == 403
    assignment.scope_grants.update(ends_at=None)
    assignment.role.is_active = False
    assignment.role.save(update_fields=["is_active"])
    assert auth_client.delete(reverse("guardian-detail", args=[guardian.pk])).status_code == 403


def test_repeated_delete_is_idempotent_and_audit_failure_rolls_back(auth_client, monkeypatch):
    guardian = GuardianFactory()
    grant(auth_client.user)

    def fail(**kwargs):
        raise RuntimeError("audit unavailable")

    with monkeypatch.context() as patch:
        patch.setattr("apps.students.services.record_event", fail)
        with pytest.raises(RuntimeError, match="audit unavailable"):
            deactivate_guardian(guardian=guardian, actor=auth_client.user)
    guardian.refresh_from_db()
    assert guardian.is_active
    url = reverse("guardian-detail", args=[guardian.pk])
    assert auth_client.delete(url).status_code == 204
    guardian.refresh_from_db()
    changed_at = guardian.updated_at
    assert auth_client.delete(url).status_code == 204
    guardian.refresh_from_db()
    assert guardian.updated_at == changed_at
    assert AuditEvent.objects.filter(action="students.guardian.deactivated").count() == 1


def test_list_capabilities_do_not_add_permission_queries_per_guardian(auth_client):
    GuardianFactory()
    grant(auth_client.user)
    url = reverse("guardian-list")
    auth_client.get(url)
    with CaptureQueriesContext(connection) as small:
        assert auth_client.get(url).json()["results"][0]["actions"] == {"deactivate": True}
    GuardianFactory.create_batch(24)
    with CaptureQueriesContext(connection) as large:
        response = auth_client.get(url).json()
        assert len(response["results"]) == 25
        assert all(row["actions"] == {"deactivate": True} for row in response["results"])
    assert len(large) <= len(small) + 1


def test_permission_migration_is_idempotent_and_does_not_grant_existing_roles():
    migration = importlib.import_module(
        "apps.students.migrations.0008_seed_guardian_deactivate_permission"
    )
    role = RoleFactory()
    editor = SimpleNamespace(connection=connection)
    migration.seed_permission(apps, editor)
    migration.seed_permission(apps, editor)
    permission = Permission.objects.get(
        content_type__app_label="identity",
        content_type__model="role",
        codename="guardian_deactivate",
    )
    assert permission.name == "Desactivar encargados"
    assert not role.permissions.exists()


def test_superuser_can_deactivate_and_nonexistent_guardian_stays_404(auth_client):
    auth_client.user.is_superuser = True
    auth_client.user.save(update_fields=["is_superuser"])
    guardian = GuardianFactory()
    assert auth_client.delete(reverse("guardian-detail", args=[guardian.pk])).status_code == 204
    assert auth_client.delete(reverse("guardian-detail", args=[999999999])).status_code == 404


def test_student_specific_scope_does_not_authorize_deactivating_guardian_roster(auth_client):
    guardian = GuardianFactory()
    relation = StudentGuardianRelationFactory(guardian=guardian)
    assignment = grant(auth_client.user, module=None)
    ScopeGrantFactory(assignment=assignment, student=relation.student)
    assert auth_client.delete(reverse("guardian-detail", args=[guardian.pk])).status_code == 403
    guardian.refresh_from_db()
    assert guardian.is_active
