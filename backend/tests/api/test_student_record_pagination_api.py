import uuid

import pytest
from django.urls import reverse
from django.utils import timezone

from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import (
    EmergencyContactFactory,
    StudentFactory,
    StudentGuardianRelationFactory,
    StudentHealthNoteFactory,
    StudentObservationFactory,
)


def grant(user, *students, codename="student_view_basic"):
    permission = PermissionFactory(codename=codename)
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    for student in students:
        ScopeGrantFactory(assignment=assignment, student=student)


@pytest.mark.api
@pytest.mark.django_db
def test_guardian_relations_filter_by_student_before_pagination(auth_client):
    other = StudentFactory()
    student = StudentFactory()
    grant(auth_client.user, student, other)
    StudentGuardianRelationFactory.create_batch(26, student=other, is_primary=False)
    relations = StudentGuardianRelationFactory.create_batch(26, student=student, is_primary=False)
    url = reverse("student-guardian-relation-list")

    first = auth_client.get(url, {"student_id": str(student.public_id)}).json()
    second = auth_client.get(url, {"student_id": str(student.public_id), "page": 2}).json()

    assert first["count"] == second["count"] == 26
    assert len(first["results"]) == 25
    assert len(second["results"]) == 1
    returned = first["results"] + second["results"]
    assert {item["id"] for item in returned} == {relation.pk for relation in relations}
    assert all(item["student"] == student.pk for item in returned)


@pytest.mark.api
@pytest.mark.django_db
def test_guardian_relations_filter_preserves_scope_and_hides_other_student(auth_client):
    allowed = StudentFactory()
    denied = StudentFactory()
    grant(auth_client.user, allowed)
    StudentGuardianRelationFactory(student=allowed)
    StudentGuardianRelationFactory(student=denied)

    response = auth_client.get(
        reverse("student-guardian-relation-list"), {"student_id": str(denied.public_id)}
    )

    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["results"] == []


@pytest.mark.api
@pytest.mark.django_db
def test_guardian_relations_filter_keeps_historical_links(auth_client):
    student = StudentFactory()
    grant(auth_client.user, student)
    current = StudentGuardianRelationFactory(student=student)
    historical = StudentGuardianRelationFactory(
        student=student, is_primary=False, ends_at=timezone.localdate(), is_active=False
    )
    response = auth_client.get(
        reverse("student-guardian-relation-list"), {"student_id": str(student.public_id)}
    )
    assert response.status_code == 200
    assert {item["id"] for item in response.json()["results"]} == {current.pk, historical.pk}


@pytest.mark.api
@pytest.mark.django_db
@pytest.mark.parametrize("student_id", ["invalid", "1", ""])
def test_guardian_relations_reject_invalid_student_filter(auth_client, student_id):
    grant(auth_client.user, StudentFactory())
    response = auth_client.get(
        reverse("student-guardian-relation-list"), {"student_id": student_id}
    )
    assert response.status_code == 400
    assert "student_id" in response.json()["error"]["detail"]


@pytest.mark.api
@pytest.mark.django_db
def test_guardian_relations_unknown_student_filter_returns_empty(auth_client):
    student = StudentFactory()
    grant(auth_client.user, student)
    StudentGuardianRelationFactory(student=student)
    response = auth_client.get(
        reverse("student-guardian-relation-list"), {"student_id": str(uuid.uuid4())}
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.api
@pytest.mark.django_db
def test_guardian_relations_student_filter_does_not_grant_permission(auth_client):
    student = StudentFactory()
    StudentGuardianRelationFactory(student=student)
    response = auth_client.get(
        reverse("student-guardian-relation-list"), {"student_id": str(student.public_id)}
    )
    assert response.status_code == 403


@pytest.mark.api
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("factory", "route"),
    [
        (StudentHealthNoteFactory, "student-health-note-list-create"),
        (StudentObservationFactory, "student-observation-list-create"),
        (EmergencyContactFactory, "student-emergency-contact-list-create"),
    ],
)
def test_sensitive_student_records_keep_all_pages_inside_scope(auth_client, factory, route):
    student = StudentFactory()
    other = StudentFactory()
    grant(auth_client.user, student, codename="student_view_sensitive")
    records = factory.create_batch(26, student=student)
    factory(student=other)
    url = reverse(route, args=[student.public_id])

    first = auth_client.get(url).json()
    second = auth_client.get(url, {"page": 2}).json()

    assert first["count"] == second["count"] == 26
    assert len(first["results"]) == 25
    assert len(second["results"]) == 1
    assert {item["public_id"] for item in first["results"] + second["results"]} == {
        str(record.public_id) for record in records
    }
    assert auth_client.get(reverse(route, args=[other.public_id])).status_code == 403


@pytest.mark.api
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("factory", "route"),
    [
        (StudentHealthNoteFactory, "student-health-note-list-create"),
        (StudentObservationFactory, "student-observation-list-create"),
    ],
)
def test_sensitive_pagination_breaks_equal_date_ties_with_record_id(auth_client, factory, route):
    student = StudentFactory()
    grant(auth_client.user, student, codename="student_view_sensitive")
    records = factory.create_batch(26, student=student)
    factory._meta.model.objects.filter(student=student).update(created_at=timezone.now())
    url = reverse(route, args=[student.public_id])

    first = auth_client.get(url).json()
    second = auth_client.get(url, {"page": 2}).json()

    assert [item["public_id"] for item in first["results"] + second["results"]] == [
        str(record.public_id) for record in reversed(records)
    ]
