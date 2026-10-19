"""#632 T3: authorized logical deactivation, atomic audit and retained history."""

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

from apps.academics.models import TeachingAssignment
from apps.audit.models import AuditEvent
from apps.teachers.services import deactivate_teacher
from tests.factories.academic import SectionFactory, SubjectFactory
from tests.factories.documents import DocumentRecordFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def grant(user, *, module="teachers"):
    assignment = RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[PermissionFactory(codename="teacher_deactivate")]),
        identity_scope=False,
    )
    if module:
        ScopeGrantFactory(assignment=assignment, module_key=module)
    return assignment


def test_deactivation_preserves_person_account_assignments_and_documents(auth_client):
    teacher = TeacherFactory()
    account = UserFactory(person=teacher.person)
    section = SectionFactory()
    assignment = TeachingAssignment.objects.create(
        teacher=teacher.person,
        section=section,
        academic_cycle=section.academic_cycle,
        subject=SubjectFactory(institution=section.academic_cycle.institution),
    )
    document = DocumentRecordFactory(student=None, teacher=teacher)
    grant(auth_client.user)
    response = auth_client.delete(reverse("teacher-detail", args=[teacher.pk]))
    assert response.status_code == 204 and response.content == b""
    teacher.refresh_from_db()
    assert not teacher.is_active
    for retained in (teacher.person, account, assignment, document):
        retained.refresh_from_db()
        assert retained.is_active
    assert assignment.ends_on is None
    assert account.person_id == teacher.person_id
    assert document.teacher_id == teacher.pk
    event = AuditEvent.objects.get(action="teachers.teacher.deactivated")
    assert event.actor == auth_client.user
    assert event.resource_identifier == str(teacher.pk)
    assert event.context["is_active"] == {"old": True, "new": False}
    detail = auth_client.get(reverse("teacher-detail", args=[teacher.pk])).json()
    assert detail["is_active"] is False and detail["actions"] == {"deactivate": False}
    assert auth_client.get(reverse("teacher-list")).json()["count"] == 0
    assert (
        auth_client.get(reverse("teacher-list"), {"include_inactive": "true"}).json()["count"] == 1
    )


@pytest.mark.parametrize("scope", [None, "students", "identity"])
def test_permission_without_teachers_scope_is_denied_and_audited(auth_client, scope):
    teacher = TeacherFactory()
    grant(auth_client.user, module=scope)
    assert auth_client.delete(reverse("teacher-detail", args=[teacher.pk])).status_code == 403
    teacher.refresh_from_db()
    assert teacher.is_active
    assert AuditEvent.objects.filter(
        actor=auth_client.user, action="identity.authorization.denied", resource="Teacher"
    ).exists()
    assert not AuditEvent.objects.filter(action="teachers.teacher.deactivated").exists()


def test_anonymous_and_session_without_permission_cannot_deactivate(auth_client):
    teacher = TeacherFactory()
    url = reverse("teacher-detail", args=[teacher.pk])
    assert Client().delete(url).status_code == 403
    assert auth_client.delete(url).status_code == 403
    assert auth_client.get(url).json()["actions"] == {"deactivate": False}


def test_capabilities_do_not_audit_unattempted_writes_and_delete_revalidates(auth_client):
    teacher = TeacherFactory()
    url = reverse("teacher-detail", args=[teacher.pk])
    assert auth_client.get(url).json()["actions"] == {"deactivate": False}
    assignment = grant(auth_client.user)
    assert auth_client.get(url).json()["actions"] == {"deactivate": True}
    assert not AuditEvent.objects.filter(action="identity.authorization.denied").exists()
    assignment.ends_at = timezone.now() - timezone.timedelta(seconds=1)
    assignment.save(update_fields=["ends_at"])
    assert auth_client.delete(url).status_code == 403
    teacher.refresh_from_db()
    assert teacher.is_active


def test_expired_scope_and_inactive_role_cannot_deactivate(auth_client):
    teacher = TeacherFactory()
    assignment = grant(auth_client.user)
    assignment.scope_grants.update(ends_at=timezone.now() - timezone.timedelta(seconds=1))
    assert auth_client.delete(reverse("teacher-detail", args=[teacher.pk])).status_code == 403
    assignment.scope_grants.update(ends_at=None)
    assignment.role.is_active = False
    assignment.role.save(update_fields=["is_active"])
    assert auth_client.delete(reverse("teacher-detail", args=[teacher.pk])).status_code == 403


def test_repeated_delete_is_idempotent_and_audit_failure_rolls_back(auth_client, monkeypatch):
    teacher = TeacherFactory()
    grant(auth_client.user)

    def fail(**kwargs):
        raise RuntimeError("audit unavailable")

    with monkeypatch.context() as patch:
        patch.setattr("apps.teachers.services.record_event", fail)
        with pytest.raises(RuntimeError, match="audit unavailable"):
            deactivate_teacher(teacher=teacher, actor=auth_client.user)
    teacher.refresh_from_db()
    assert teacher.is_active
    url = reverse("teacher-detail", args=[teacher.pk])
    assert auth_client.delete(url).status_code == 204
    teacher.refresh_from_db()
    changed_at = teacher.updated_at
    assert auth_client.delete(url).status_code == 204
    teacher.refresh_from_db()
    assert teacher.updated_at == changed_at
    assert AuditEvent.objects.filter(action="teachers.teacher.deactivated").count() == 1


def test_list_capabilities_do_not_add_permission_queries_per_teacher(auth_client):
    TeacherFactory()
    grant(auth_client.user)
    url = reverse("teacher-list")
    auth_client.get(url)
    with CaptureQueriesContext(connection) as small:
        assert auth_client.get(url).json()["results"][0]["actions"] == {"deactivate": True}
    TeacherFactory.create_batch(24)
    with CaptureQueriesContext(connection) as large:
        response = auth_client.get(url).json()
        assert len(response["results"]) == 25
        assert all(row["actions"] == {"deactivate": True} for row in response["results"])
    assert len(large) <= len(small) + 1


def test_permission_migration_is_idempotent_and_does_not_grant_existing_roles():
    migration = importlib.import_module(
        "apps.identity.migrations.0018_seed_teacher_deactivate_permission"
    )
    role = RoleFactory()
    editor = SimpleNamespace(connection=connection)
    migration.seed_permission(apps, editor)
    migration.seed_permission(apps, editor)
    permission = Permission.objects.get(
        content_type__app_label="identity",
        content_type__model="role",
        codename="teacher_deactivate",
    )
    assert permission.name == "Desactivar docentes"
    assert not role.permissions.exists()


def test_superuser_can_deactivate_and_nonexistent_teacher_stays_404(auth_client):
    auth_client.user.is_superuser = True
    auth_client.user.save(update_fields=["is_superuser"])
    teacher = TeacherFactory()
    assert auth_client.delete(reverse("teacher-detail", args=[teacher.pk])).status_code == 204
    assert auth_client.delete(reverse("teacher-detail", args=[999999999])).status_code == 404
