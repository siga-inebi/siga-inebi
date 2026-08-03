import pytest
from django.urls import reverse

from apps.students.models import Student
from tests.factories.identity import UserFactory
from tests.factories.people import PersonFactory
from tests.factories.students import StudentFactory


@pytest.fixture
def logged_in_client(client):
    user = UserFactory(password="test-pass-123")
    client.login(username=user.username, password="test-pass-123")
    return client


@pytest.mark.api
@pytest.mark.django_db
def test_create_student(logged_in_client):
    person = PersonFactory()
    payload = {
        "person": person.pk,
        "student_code": "STU-1000",
        "status": Student.StudentStatus.PRE_ENROLLED,
    }

    response = logged_in_client.post(reverse("student-list"), payload)

    assert response.status_code == 201
    data = response.json()
    assert data["student_code"] == "STU-1000"
    assert data["is_active"] is True
    assert Student.objects.filter(pk=data["id"]).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_list_students_is_paginated(logged_in_client):
    StudentFactory.create_batch(3)

    response = logged_in_client.get(reverse("student-list"))

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] == Student.objects.count()


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_student(logged_in_client):
    student = StudentFactory()

    response = logged_in_client.get(reverse("student-detail", args=[student.pk]))

    assert response.status_code == 200
    assert response.json()["id"] == student.pk


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_missing_student_returns_404(logged_in_client):
    response = logged_in_client.get(reverse("student-detail", args=[999999]))

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_update_student(logged_in_client):
    student = StudentFactory(status=Student.StudentStatus.PRE_ENROLLED)

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

    response = logged_in_client.delete(reverse("student-detail", args=[student.pk]))

    assert response.status_code == 204
    student.refresh_from_db()
    assert student.is_active is False
    assert student.status == Student.StudentStatus.INACTIVE
    assert Student.objects.filter(pk=student.pk).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_create_student_duplicate_student_code_is_rejected(logged_in_client):
    existing = StudentFactory(student_code="STU-2000")
    person = PersonFactory()

    response = logged_in_client.post(
        reverse("student-list"),
        {
            "person": person.pk,
            "student_code": existing.student_code,
            "status": Student.StudentStatus.PRE_ENROLLED,
        },
    )

    assert response.status_code == 400
    detail = response.json()["error"]["detail"]
    assert "student_code" in detail


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_is_rejected(client):
    response = client.get(reverse("student-list"))

    assert response.status_code == 403
