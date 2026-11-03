from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import StudentGuardianRelationFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def grant(user, student, permission):
    role = RoleFactory(permissions=[PermissionFactory(codename=permission)])
    ScopeGrantFactory(assignment=RoleAssignmentFactory(user=user, role=role), student=student)


def record_url(relation):
    return reverse("student-record-guardians", kwargs={"public_id": relation.student.public_id})


def test_patch_preserves_identity_primary_dates_history_and_audits(auth_client):
    relation = StudentGuardianRelationFactory(
        relationship_label="Madre",
        ends_at=timezone.localdate(),
        is_primary=False,
    )
    before = (
        relation.student_id,
        relation.guardian_id,
        relation.starts_at,
        relation.ends_at,
        relation.is_primary,
        relation.is_active,
    )
    grant(auth_client.user, relation.student, "student_edit_basic")
    response = auth_client.patch(
        reverse("student-guardian-relation-detail", args=[relation.pk]),
        {"relationship_label": "  Responsable  "},
        content_type="application/json",
    )
    assert response.status_code == 200
    relation.refresh_from_db()
    assert relation.relationship_label == "Responsable"
    assert before == (
        relation.student_id,
        relation.guardian_id,
        relation.starts_at,
        relation.ends_at,
        relation.is_primary,
        relation.is_active,
    )
    event = AuditEvent.objects.get(action="students.student_guardian_relation.updated")
    assert event.actor == auth_client.user
    assert event.context["changes"] == {
        "relationship_label": {"before": "Madre", "after": "Responsable"}
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"relationship_label": " "},
        {"relationship_label": "x" * 101},
        {"relationship_label": "Tutor", "is_primary": True},
        {"relationship_label": "Tutor", "ends_at": None},
        {"relationship_label": "Tutor", "student": 99999},
        {"relationship_label": "Tutor", "guardian": 99999},
        {"relationship_label": "Tutor", "starts_at": "2000-01-01"},
    ],
)
def test_patch_rejects_invalid_or_protected_fields(auth_client, payload):
    relation = StudentGuardianRelationFactory(relationship_label="Madre")
    grant(auth_client.user, relation.student, "student_edit_basic")
    response = auth_client.patch(
        reverse("student-guardian-relation-detail", args=[relation.pk]),
        payload,
        content_type="application/json",
    )
    assert response.status_code == 400
    relation.refresh_from_db()
    assert relation.relationship_label == "Madre"
    assert not AuditEvent.objects.filter(
        action="students.student_guardian_relation.updated"
    ).exists()


def test_patch_requires_edit_permission_and_matching_scope(auth_client):
    allowed, other = StudentGuardianRelationFactory.create_batch(2)
    url = reverse("student-guardian-relation-detail", args=[allowed.pk])
    data = {"relationship_label": "Tutor"}
    assert Client().patch(url, data, content_type="application/json").status_code == 403
    grant(auth_client.user, allowed.student, "student_view_basic")
    assert auth_client.patch(url, data, content_type="application/json").status_code == 403
    grant(auth_client.user, other.student, "student_edit_basic")
    assert auth_client.patch(url, data, content_type="application/json").status_code == 404
    allowed.refresh_from_db()
    assert allowed.relationship_label != "Tutor"


def test_record_actions_come_from_scope_and_relation_state(auth_client):
    primary = StudentGuardianRelationFactory()
    current = StudentGuardianRelationFactory(student=primary.student, is_primary=False)
    ended = StudentGuardianRelationFactory(
        student=primary.student,
        is_primary=False,
        ends_at=timezone.localdate(),
    )
    grant(auth_client.user, primary.student, "student_view_basic")
    rows = auth_client.get(record_url(primary)).json()["results"]
    assert not AuditEvent.objects.filter(action="identity.authorization.denied").exists()
    assert all(not row["actions"][key] for row in rows for key in ("edit", "make_primary", "end"))
    grant(auth_client.user, primary.student, "student_edit_basic")
    rows = {
        row["id"]: row["actions"] for row in auth_client.get(record_url(primary)).json()["results"]
    }
    assert rows[primary.pk] == {
        "edit": True,
        "make_primary": False,
        "end": True,
        "offers_replacement": True,
    }
    assert rows[current.pk]["make_primary"] is True
    assert rows[ended.pk] == {
        "edit": True,
        "make_primary": False,
        "end": False,
        "offers_replacement": False,
    }


def test_replacement_list_filters_before_pagination_and_never_crosses_students(auth_client):
    primary = StudentGuardianRelationFactory()
    replacements = StudentGuardianRelationFactory.create_batch(
        26,
        student=primary.student,
        is_primary=False,
    )
    StudentGuardianRelationFactory(student=primary.student, is_primary=False, is_active=False)
    StudentGuardianRelationFactory(
        student=primary.student, is_primary=False, ends_at=timezone.localdate()
    )
    StudentGuardianRelationFactory(
        student=primary.student,
        is_primary=False,
        starts_at=timezone.localdate() + timedelta(days=1),
    )
    other = StudentGuardianRelationFactory()
    grant(auth_client.user, primary.student, "student_view_basic")
    seen = []
    for page in (1, 2):
        response = auth_client.get(
            record_url(primary), {"replacement_for": primary.pk, "page": page}
        )
        assert response.status_code == 200
        assert response.json()["count"] == 26
        seen += [row["id"] for row in response.json()["results"]]
    assert set(seen) == {row.pk for row in replacements}
    assert len(seen) == len(set(seen))
    assert auth_client.get(record_url(primary), {"replacement_for": other.pk}).status_code == 404
    assert auth_client.get(record_url(primary), {"replacement_for": "invalid"}).status_code == 400


def test_end_rejects_other_student_replacement_without_partial_writes(auth_client):
    primary = StudentGuardianRelationFactory()
    other = StudentGuardianRelationFactory()
    grant(auth_client.user, primary.student, "student_edit_basic")
    response = auth_client.post(
        reverse("student-guardian-relation-end", args=[primary.pk]),
        {"replacement_relation": other.pk},
        content_type="application/json",
    )
    assert response.status_code == 400
    primary.refresh_from_db()
    other.refresh_from_db()
    assert primary.is_primary and primary.ends_at is None
    assert other.is_primary and other.ends_at is None
    assert not AuditEvent.objects.filter(action="students.student_guardian_relation.ended").exists()
