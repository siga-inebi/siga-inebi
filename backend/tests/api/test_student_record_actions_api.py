import json

import pytest
from django.test import Client
from django.urls import reverse

from apps.audit.models import AuditEvent
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import (
    EmergencyContactFactory,
    StudentFactory,
    StudentHealthNoteFactory,
    StudentObservationFactory,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]
CASES = [
    (
        StudentHealthNoteFactory,
        "student-health-note-detail",
        "student-health-note-list-create",
        "content",
        "health_note",
    ),
    (
        StudentObservationFactory,
        "student-observation-detail",
        "student-observation-list-create",
        "description",
        "observation",
    ),
    (
        EmergencyContactFactory,
        "emergency-contact-detail",
        "student-emergency-contact-list-create",
        "name",
        "emergency_contact",
    ),
]


def grant(user, student, *codenames):
    assignment = RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[PermissionFactory(codename=name) for name in codenames]),
    )
    ScopeGrantFactory(assignment=assignment, student=student)


@pytest.mark.parametrize("factory,detail,listing,field,action", CASES)
def test_edit_preserves_metadata_and_audits_without_content(
    auth_client, factory, detail, listing, field, action
):
    record = factory()
    before = {
        name: getattr(record, name)
        for name in (
            "student_id",
            "created_at",
            "is_active",
            "public_id",
            "author_id",
            "recorded_on",
            "observed_on",
        )
        if hasattr(record, name)
    }
    grant(auth_client.user, record.student, "student_view_sensitive", "student_edit_basic")
    response = auth_client.patch(
        reverse(detail, args=[record.public_id]),
        {field: "  Contenido sintetico corregido  "},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()[field] == "Contenido sintetico corregido"
    record.refresh_from_db()
    assert {name: getattr(record, name) for name in before} == before
    event = AuditEvent.objects.get(action=f"students.{action}.updated")
    assert event.actor == auth_client.user
    assert event.context["fields"] == [field]
    assert "Contenido sintetico" not in json.dumps(
        list(AuditEvent.objects.values_list("context", flat=True))
    )


@pytest.mark.parametrize("factory,detail,listing,field,action", CASES)
def test_soft_delete_and_include_inactive_keep_history_and_allow_correction_without_reactivation(
    auth_client, factory, detail, listing, field, action
):
    record = factory()
    original = getattr(record, field)
    grant(auth_client.user, record.student, "student_view_sensitive", "student_edit_basic")
    detail_url = reverse(detail, args=[record.public_id])
    list_url = reverse(listing, args=[record.student.public_id])
    assert auth_client.delete(detail_url).status_code == 204
    record.refresh_from_db()
    assert record.is_active is False and getattr(record, field) == original
    assert auth_client.get(list_url).json()["count"] == 0
    response = auth_client.get(list_url, {"include_inactive": "true"})
    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["public_id"] == str(record.public_id)
    assert row["actions"] == {"edit": True, "deactivate": False}
    assert row[field] == original
    assert response.headers["Cache-Control"] == "no-store"
    assert AuditEvent.objects.filter(action=f"students.{action}.deactivated").exists()
    assert (
        auth_client.patch(
            detail_url, {field: "Correccion historica sintetica"}, content_type="application/json"
        ).status_code
        == 200
    )
    record.refresh_from_db()
    assert record.is_active is False


@pytest.mark.parametrize("factory,detail,listing,field,action", CASES)
def test_write_requires_both_permissions_and_scope_and_list_hides_actions(
    auth_client, factory, detail, listing, field, action
):
    record = factory()
    url = reverse(detail, args=[record.public_id])
    payload = {field: "No debe persistirse"}
    assert Client().patch(url, payload, content_type="application/json").status_code == 403
    assert Client().delete(url).status_code == 403
    grant(auth_client.user, record.student, "student_view_sensitive")
    rows = auth_client.get(reverse(listing, args=[record.student.public_id])).json()["results"]
    assert rows[0]["actions"] == {"edit": False, "deactivate": False}
    assert not AuditEvent.objects.filter(action="identity.authorization.denied").exists()
    assert auth_client.patch(url, payload, content_type="application/json").status_code == 403
    assert auth_client.delete(url).status_code == 403
    grant(auth_client.user, StudentFactory(), "student_edit_basic")
    assert auth_client.patch(url, payload, content_type="application/json").status_code == 403
    assert auth_client.delete(url).status_code == 403
    record.refresh_from_db()
    assert record.is_active and getattr(record, field) != payload[field]
    assert not AuditEvent.objects.filter(action=f"students.{action}.updated").exists()


@pytest.mark.parametrize("factory,detail,listing,field,action", CASES)
def test_edit_without_sensitive_permission_is_denied(
    auth_client, factory, detail, listing, field, action
):
    record = factory()
    grant(auth_client.user, record.student, "student_edit_basic")
    url = reverse(detail, args=[record.public_id])
    assert (
        auth_client.patch(
            url, {field: "No autorizado"}, content_type="application/json"
        ).status_code
        == 403
    )
    assert auth_client.delete(url).status_code == 403


@pytest.mark.parametrize("factory,detail,listing,field,action", CASES[:2])
@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"author": "otro"},
        {"student": "otro"},
        {"recorded_on": "2000-01-01"},
        {"observed_on": "2000-01-01"},
        {"is_active": False},
    ],
)
def test_new_patch_rejects_missing_or_protected_fields(
    auth_client, factory, detail, listing, field, action, extra
):
    record = factory()
    grant(auth_client.user, record.student, "student_view_sensitive", "student_edit_basic")
    payload = {field: "Corregido", **extra} if extra else {}
    response = auth_client.patch(
        reverse(detail, args=[record.public_id]), payload, content_type="application/json"
    )
    assert response.status_code == 400
    assert not AuditEvent.objects.filter(action=f"students.{action}.updated").exists()


@pytest.mark.parametrize("factory,detail,listing,field,action", CASES)
def test_blank_edit_is_rejected_without_changes(
    auth_client, factory, detail, listing, field, action
):
    record = factory()
    original = getattr(record, field)
    grant(auth_client.user, record.student, "student_view_sensitive", "student_edit_basic")
    assert (
        auth_client.patch(
            reverse(detail, args=[record.public_id]), {field: " "}, content_type="application/json"
        ).status_code
        == 400
    )
    record.refresh_from_db()
    assert getattr(record, field) == original


@pytest.mark.parametrize("factory,detail,listing,field,action", CASES)
def test_historical_pages_are_scoped_before_count_and_pagination(
    auth_client, factory, detail, listing, field, action
):
    student = StudentFactory()
    own = factory.create_batch(26, student=student, is_active=False)
    factory.create_batch(26, is_active=False)
    grant(auth_client.user, student, "student_view_sensitive", "student_edit_basic")
    url = reverse(listing, args=[student.public_id])
    seen = []
    for page in (1, 2):
        response = auth_client.get(url, {"include_inactive": "true", "page": page})
        assert response.json()["count"] == 26
        seen += [row["public_id"] for row in response.json()["results"]]
    assert len(seen) == len(set(seen)) == 26
    assert set(seen) == {str(row.public_id) for row in own}
