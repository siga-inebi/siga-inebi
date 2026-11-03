"""#632 G4: scoped, paginated guardian links and an atomic linking workflow."""

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.people.models import Person
from apps.students import services
from apps.students.models import Student, StudentGuardianRelation
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import GuardianFactory, StudentFactory, StudentGuardianRelationFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def grant(user, codename, *, student=None, module=None):
    assignment = RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[PermissionFactory(codename=codename)]),
        identity_scope=False,
    )
    if student or module:
        ScopeGrantFactory(assignment=assignment, student=student, module_key=module or "")
    return assignment


def test_links_filter_scope_before_count_and_pagination_and_keep_history(auth_client):
    guardian = GuardianFactory()
    visible = [StudentFactory() for _ in range(26)]
    for student in visible:
        grant(auth_client.user, "student_view_basic", student=student)
        StudentGuardianRelationFactory(guardian=guardian, student=student)
    StudentGuardianRelationFactory(guardian=guardian)  # Outside scope, never counted.
    historical = StudentGuardianRelationFactory(
        guardian=guardian, student=visible[0], is_active=False, ends_at=timezone.localdate()
    )
    url = reverse("guardian-students", args=[guardian.pk])
    first = auth_client.get(url).json()
    assert auth_client.get(url)["Cache-Control"] == "no-store"
    last = auth_client.get(url, {"page": 2}).json()
    assert first["count"] == last["count"] == 27
    assert len(first["results"]) == 25 and len(last["results"]) == 2
    rows = first["results"] + last["results"]
    assert len({row["id"] for row in rows}) == 27
    assert historical.pk in {row["id"] for row in rows}
    assert {row["student"]["public_id"] for row in rows} == {
        str(student.public_id) for student in visible
    }
    assert set(rows[0]["student"]) == {
        "public_id",
        "student_code",
        "full_name",
        "is_active",
        "status",
    }
    assert first["actions"] == {"link_student": False}


@pytest.mark.parametrize("scope", [None, "teachers"])
def test_permission_without_student_scope_is_denied_and_audited(auth_client, scope):
    guardian = GuardianFactory()
    grant(auth_client.user, "student_view_basic", module=scope)
    response = auth_client.get(reverse("guardian-students", args=[guardian.pk]))
    if scope is None:
        assert response.status_code == 403
        assert AuditEvent.objects.filter(
            action="identity.authorization.denied", actor=auth_client.user
        ).exists()
    else:
        assert response.status_code == 200
        assert response.json()["count"] == 0
        assert response.json()["actions"] == {"link_student": False}


def test_session_is_not_enough_and_missing_guardian_is_404(auth_client):
    guardian = GuardianFactory()
    url = reverse("guardian-students", args=[guardian.pk])
    assert Client().get(url).status_code == 403
    assert auth_client.get(url).status_code == 403
    grant(auth_client.user, "student_view_basic", module="students")
    assert auth_client.get(reverse("guardian-students", args=[9999999])).status_code == 404


def test_candidates_require_both_scopes_and_filter_before_pagination(auth_client):
    guardian = GuardianFactory()
    read_only = StudentFactory(student_code="G4-READ")
    editable_only = StudentFactory(student_code="G4-EDIT")
    match = StudentFactory(student_code="G4-MATCH")
    grant(auth_client.user, "student_view_basic", student=read_only)
    grant(auth_client.user, "student_edit_basic", student=editable_only)
    for code in ("student_view_basic", "student_edit_basic"):
        grant(auth_client.user, code, student=match)
    url = reverse("guardian-student-candidates", args=[guardian.pk])
    assert auth_client.get(url).json()["count"] == 0
    response = auth_client.get(url, {"search": "G4"}).json()
    assert [row["public_id"] for row in response["results"]] == [str(match.public_id)]
    StudentGuardianRelationFactory(guardian=guardian, student=match)
    assert auth_client.get(url, {"search": "G4"}).json()["count"] == 0
    assert auth_client.get(reverse("guardian-students", args=[guardian.pk])).json()["actions"] == {
        "link_student": False
    }


def test_create_link_is_audited_primary_when_first_and_rejects_duplicate(auth_client):
    guardian = GuardianFactory()
    student = StudentFactory()
    for code in ("student_view_basic", "student_edit_basic"):
        grant(auth_client.user, code, student=student)
    url = reverse("guardian-students", args=[guardian.pk])
    assert auth_client.get(url).json()["actions"] == {"link_student": True}
    payload = {"student_public_id": str(student.public_id), "relationship_label": "Responsable"}
    created = auth_client.post(url, payload, content_type="application/json")
    assert created.status_code == 201
    assert created.json()["is_primary"] is True
    assert created.json()["student"]["public_id"] == str(student.public_id)
    assert StudentGuardianRelation.objects.filter(guardian=guardian, student=student).count() == 1
    assert auth_client.post(url, payload, content_type="application/json").status_code == 400
    assert (
        AuditEvent.objects.filter(action="students.student_guardian_relation.created").count() == 1
    )


def test_ended_relation_can_be_linked_again_without_overwriting_history(auth_client):
    guardian = GuardianFactory()
    historical = StudentGuardianRelationFactory(
        guardian=guardian, ends_at=timezone.localdate(), is_primary=False
    )
    for code in ("student_view_basic", "student_edit_basic"):
        grant(auth_client.user, code, student=historical.student)
    response = auth_client.post(
        reverse("guardian-students", args=[guardian.pk]),
        {
            "student_public_id": str(historical.student.public_id),
            "relationship_label": "Nuevo vinculo",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    historical.refresh_from_db()
    assert historical.ends_at == timezone.localdate()
    assert StudentGuardianRelation.objects.filter(guardian=guardian).count() == 2


@pytest.mark.parametrize("inactive", ["guardian", "person", "student", "status"])
def test_stale_selection_rechecks_active_profiles(auth_client, inactive):
    guardian = GuardianFactory()
    student = StudentFactory()
    for code in ("student_view_basic", "student_edit_basic"):
        grant(auth_client.user, code, student=student)
    if inactive == "status":
        student.status = Student.StudentStatus.WITHDRAWN
        student.save(update_fields=["status"])
    else:
        target = {"guardian": guardian, "person": guardian.person, "student": student}[inactive]
        target.is_active = False
        target.save(update_fields=["is_active"])
    response = auth_client.post(
        reverse("guardian-students", args=[guardian.pk]),
        {"student_public_id": str(student.public_id), "relationship_label": "Responsable"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert not StudentGuardianRelation.objects.exists()


def test_write_revalidates_scope_and_rejects_other_student(auth_client):
    guardian = GuardianFactory()
    own, other = StudentFactory(), StudentFactory()
    grant(auth_client.user, "student_view_basic", module="students")
    assignment = grant(auth_client.user, "student_edit_basic", student=own)
    url = reverse("guardian-students", args=[guardian.pk])
    assert (
        auth_client.post(
            url,
            {"student_public_id": str(other.public_id), "relationship_label": "Familiar"},
            content_type="application/json",
        ).status_code
        == 404
    )
    assignment.ends_at = timezone.now() - timezone.timedelta(seconds=1)
    assert AuditEvent.objects.filter(
        action="identity.authorization.denied",
        resource_identifier=str(other.public_id),
        context__reason="not_found_or_outside_scope",
    ).exists()
    assignment.save(update_fields=["ends_at"])
    assert (
        auth_client.post(
            url,
            {"student_public_id": str(own.public_id), "relationship_label": "Familiar"},
            content_type="application/json",
        ).status_code
        == 403
    )
    assert not StudentGuardianRelation.objects.exists()


def test_audit_failure_rolls_back_and_unknown_payload_fields_are_rejected(auth_client, monkeypatch):
    guardian, student = GuardianFactory(), StudentFactory()
    for code in ("student_view_basic", "student_edit_basic"):
        grant(auth_client.user, code, student=student)

    def fail(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("apps.students.services.record_event", fail)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        services.link_student_from_guardian(
            actor=auth_client.user,
            guardian_id=guardian.pk,
            student_public_id=student.public_id,
            relationship_label="Familiar",
        )
    assert not StudentGuardianRelation.objects.exists()
    payload = {
        "student_public_id": str(student.public_id),
        "relationship_label": "Familiar",
        "is_primary": True,
    }
    assert (
        auth_client.post(
            reverse("guardian-students", args=[guardian.pk]),
            payload,
            content_type="application/json",
        ).status_code
        == 400
    )


def test_rows_expose_end_only_for_current_links_the_actor_can_edit(auth_client):
    guardian = GuardianFactory()
    editable, read_only, ended = StudentFactory(), StudentFactory(), StudentFactory()
    for student in (editable, read_only, ended):
        grant(auth_client.user, "student_view_basic", student=student)
    for student in (editable, ended):
        grant(auth_client.user, "student_edit_basic", student=student)
    StudentGuardianRelationFactory(guardian=guardian, student=editable, is_primary=True)
    StudentGuardianRelationFactory(guardian=guardian, student=read_only, is_primary=False)
    StudentGuardianRelationFactory(
        guardian=guardian, student=ended, is_primary=False, ends_at=timezone.localdate()
    )
    rows = auth_client.get(reverse("guardian-students", args=[guardian.pk])).json()["results"]
    actions = {row["student"]["public_id"]: row["actions"] for row in rows}
    assert actions[str(editable.public_id)]["end"] is True
    assert actions[str(editable.public_id)]["offers_replacement"] is True
    assert actions[str(read_only.public_id)]["end"] is False
    assert actions[str(ended.public_id)]["end"] is False


def test_linked_student_names_do_not_add_queries_per_row(auth_client):
    guardian = GuardianFactory()
    grant(auth_client.user, "student_view_basic", module="students")
    StudentGuardianRelationFactory(guardian=guardian)
    url = reverse("guardian-students", args=[guardian.pk])
    auth_client.get(url)
    with CaptureQueriesContext(connection) as small:
        assert auth_client.get(url).status_code == 200
    StudentGuardianRelationFactory.create_batch(24, guardian=guardian)
    with CaptureQueriesContext(connection) as large:
        assert len(auth_client.get(url).json()["results"]) == 25
    assert len(large) <= len(small) + 1


def test_link_roster_beyond_one_thousand_and_candidates_filtered_before_pagination(auth_client):
    guardian = GuardianFactory()
    people = Person.objects.bulk_create(
        [Person(first_name="AlumnoG4", last_name=f"Volumen {index:04d}") for index in range(1001)]
    )
    students = Student.objects.bulk_create(
        [
            Student(
                person=person,
                student_code=f"G4-VOL-{index:04d}",
                status=Student.StudentStatus.ACTIVE,
            )
            for index, person in enumerate(people)
        ]
    )
    StudentGuardianRelation.objects.bulk_create(
        [
            StudentGuardianRelation(
                guardian=guardian, student=student, relationship_label="Familiar"
            )
            for student in students
        ]
    )
    for code in ("student_view_basic", "student_edit_basic"):
        grant(auth_client.user, code, module="students")
    response = auth_client.get(reverse("guardian-students", args=[guardian.pk]), {"page": 41})
    assert response.status_code == 200
    assert response.json()["count"] == 1001
    assert len(response.json()["results"]) == 1
    assert response.json()["next"] is None
    another = GuardianFactory()
    candidates = auth_client.get(
        reverse("guardian-student-candidates", args=[another.pk]), {"search": "G4-VOL-1000"}
    )
    assert candidates.status_code == 200
    assert candidates.json()["count"] == 1
    assert candidates.json()["results"][0]["student_code"] == "G4-VOL-1000"


def test_linked_students_schema_documents_pagination_and_actions():
    from django.urls import path
    from drf_spectacular.generators import SchemaGenerator

    from apps.students.api.guardian_records import GuardianStudentsView

    schema = SchemaGenerator(
        patterns=[path("guardians/<int:pk>/students/", GuardianStudentsView.as_view())]
    ).get_schema(request=None, public=True)
    operation = next(iter(schema["paths"].values()))["get"]
    assert {"page", "page_size"}.issubset(
        {parameter["name"] for parameter in operation["parameters"]}
    )
    response = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response["$ref"].endswith("/GuardianStudentsPage")
