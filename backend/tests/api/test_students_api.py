import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.urls import reverse

from apps.enrolments.services import create_enrolment
from apps.people.models import Person
from apps.students.models import Student
from tests.factories.academic import AcademicCycleFactory, InstitutionFactory, SectionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.students import StudentFactory


@pytest.fixture
def logged_in_client(client):
    user = UserFactory(password="test-pass-123")
    client.login(username=user.username, password="test-pass-123")
    client.user = user
    return client


def grant_student_permission(user, codename="student_view_basic", **scope):
    permission = PermissionFactory(codename=codename)
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    return ScopeGrantFactory(assignment=assignment, **scope)


@pytest.mark.api
@pytest.mark.django_db
def test_create_student(logged_in_client):
    person_count = Person.objects.count()
    payload = {
        "person": {
            "first_name": "Maria",
            "last_name": "Lopez",
            "email": "maria.lopez@example.test",
            "phone_number": "55501234",
        },
        "student_code": "STU-1000",
        "status": Student.StudentStatus.PRE_ENROLLED,
    }

    response = logged_in_client.post(
        reverse("student-list"), payload, content_type="application/json"
    )

    assert response.status_code == 201
    data = response.json()
    assert data["student_code"] == "STU-1000"
    assert data["is_active"] is True
    assert isinstance(data["person"], dict)
    assert data["person"]["first_name"] == "Maria"
    assert data["person"]["last_name"] == "Lopez"
    assert Student.objects.filter(pk=data["id"]).exists()
    assert Person.objects.count() == person_count + 1


@pytest.mark.api
@pytest.mark.django_db
def test_create_student_missing_person_fields_is_rejected(logged_in_client):
    payload = {
        "person": {},
        "student_code": "STU-1001",
        "status": Student.StudentStatus.PRE_ENROLLED,
    }

    response = logged_in_client.post(
        reverse("student-list"), payload, content_type="application/json"
    )

    assert response.status_code == 400
    detail = response.json()["error"]["detail"]
    assert "person" in detail
    assert "first_name" in detail["person"]
    assert "last_name" in detail["person"]


@pytest.mark.api
@pytest.mark.django_db
def test_list_students_is_paginated(logged_in_client):
    students = StudentFactory.create_batch(3)
    first_grant = grant_student_permission(logged_in_client.user, student=students[0])
    for student in students[1:]:
        ScopeGrantFactory(assignment=first_grant.assignment, student=student)

    response = logged_in_client.get(reverse("student-list"))

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] == len(students)


@pytest.mark.api
@pytest.mark.django_db
def test_list_students_returns_nested_person(logged_in_client):
    student = StudentFactory()
    grant_student_permission(logged_in_client.user, student=student)

    response = logged_in_client.get(reverse("student-list"))

    assert response.status_code == 200
    results = response.json()["results"]
    match = next(item for item in results if item["id"] == student.pk)
    assert isinstance(match["person"], dict)
    assert match["person"]["first_name"] == student.person.first_name
    assert match["person"]["last_name"] == student.person.last_name


@pytest.mark.api
@pytest.mark.django_db
def test_list_students_permission_without_scope_is_denied(logged_in_client):
    permission = PermissionFactory(codename="student_view_basic")
    RoleAssignmentFactory(user=logged_in_client.user, role=RoleFactory(permissions=[permission]))

    response = logged_in_client.get(reverse("student-list"))

    assert response.status_code == 403


@pytest.mark.api
@pytest.mark.django_db
def test_list_students_is_restricted_to_section_scope(logged_in_client):
    institution = InstitutionFactory()
    academic_cycle = AcademicCycleFactory(institution=institution)
    allowed_section = SectionFactory(academic_cycle=academic_cycle)
    denied_section = SectionFactory(academic_cycle=academic_cycle, name="Z")
    allowed_student = StudentFactory()
    denied_student = StudentFactory()
    create_enrolment(
        student=allowed_student,
        academic_cycle=academic_cycle,
        grade=allowed_section.grade,
        section=allowed_section,
    )
    create_enrolment(
        student=denied_student,
        academic_cycle=academic_cycle,
        grade=denied_section.grade,
        section=denied_section,
    )
    grant_student_permission(logged_in_client.user, section=allowed_section)

    response = logged_in_client.get(reverse("student-list"))

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == allowed_student.pk


@pytest.mark.api
@pytest.mark.django_db
def test_upload_student_photo(logged_in_client):
    student = StudentFactory()
    grant_student_permission(
        logged_in_client.user,
        codename="student_edit_basic",
        student=student,
    )
    photo = SimpleUploadedFile("photo.jpg", b"fake-image-bytes", content_type="image/jpeg")

    response = logged_in_client.patch(
        reverse("student-detail", args=[student.pk]),
        data=encode_multipart(BOUNDARY, {"photo": photo}),
        content_type=MULTIPART_CONTENT,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["photo"]
    student.refresh_from_db()
    assert student.photo.name


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_student(logged_in_client):
    student = StudentFactory()
    grant_student_permission(logged_in_client.user, student=student)

    response = logged_in_client.get(reverse("student-detail", args=[student.pk]))

    assert response.status_code == 200
    assert response.json()["id"] == student.pk


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_missing_student_returns_404(logged_in_client):
    grant_student_permission(logged_in_client.user, student=StudentFactory())

    response = logged_in_client.get(reverse("student-detail", args=[999999]))

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_update_student(logged_in_client):
    student = StudentFactory(status=Student.StudentStatus.PRE_ENROLLED)
    grant_student_permission(
        logged_in_client.user,
        codename="student_edit_basic",
        student=student,
    )

    response = logged_in_client.patch(
        reverse("student-detail", args=[student.pk]),
        {"status": Student.StudentStatus.ACTIVE},
        content_type="application/json",
    )

    assert response.status_code == 200
    student.refresh_from_db()
    assert student.status == Student.StudentStatus.ACTIVE


@pytest.mark.api
@pytest.mark.django_db
def test_deactivate_student_via_delete_is_soft(logged_in_client):
    student = StudentFactory(status=Student.StudentStatus.ACTIVE)
    grant_student_permission(
        logged_in_client.user,
        codename="student_edit_basic",
        student=student,
    )

    response = logged_in_client.delete(reverse("student-detail", args=[student.pk]))

    assert response.status_code == 204
    student.refresh_from_db()
    assert student.is_active is False
    assert student.status == Student.StudentStatus.INACTIVE
    assert Student.objects.filter(pk=student.pk).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_student_outside_scope_is_denied(logged_in_client):
    allowed_student = StudentFactory()
    denied_student = StudentFactory()
    grant_student_permission(logged_in_client.user, student=allowed_student)

    response = logged_in_client.get(reverse("student-detail", args=[denied_student.pk]))

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_create_student_duplicate_student_code_is_rejected(logged_in_client):
    existing = StudentFactory(student_code="STU-2000")
    person_count = Person.objects.count()

    response = logged_in_client.post(
        reverse("student-list"),
        {
            "person": {"first_name": "Ana", "last_name": "Ramirez"},
            "student_code": existing.student_code,
            "status": Student.StudentStatus.PRE_ENROLLED,
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    detail = response.json()["error"]["detail"]
    assert "student_code" in detail
    assert Person.objects.count() == person_count


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_is_rejected(client):
    response = client.get(reverse("student-list"))

    assert response.status_code == 403
