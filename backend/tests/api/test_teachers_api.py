import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.urls import reverse

from apps.people.models import Person
from apps.teachers.models import Teacher
from tests.factories.identity import UserFactory
from tests.factories.teachers import TeacherFactory


@pytest.fixture
def logged_in_client(client):
    user = UserFactory(password="test-pass-123")
    client.login(username=user.username, password="test-pass-123")
    return client


@pytest.mark.api
@pytest.mark.django_db
def test_create_teacher(logged_in_client):
    person_count = Person.objects.count()
    payload = {
        "person": {
            "first_name": "Marvin",
            "last_name": "Lopez",
            "email": "marvin.lopez@example.test",
            "phone_number": "55661234",
        },
        "employee_code": "EMP-1000",
        "specialty": "Electricidad Industrial",
        "position": Teacher.Position.DOCENTE_TITULADO,
    }

    response = logged_in_client.post(
        reverse("teacher-list"), payload, content_type="application/json"
    )

    assert response.status_code == 201
    data = response.json()
    assert data["employee_code"] == "EMP-1000"
    assert data["is_active"] is True
    assert isinstance(data["person"], dict)
    assert data["person"]["first_name"] == "Marvin"
    assert data["person"]["last_name"] == "Lopez"
    assert Teacher.objects.filter(pk=data["id"]).exists()
    assert Person.objects.count() == person_count + 1


@pytest.mark.api
@pytest.mark.django_db
def test_create_teacher_missing_person_fields_is_rejected(logged_in_client):
    payload = {
        "person": {},
        "employee_code": "EMP-1001",
        "specialty": "Matematica",
        "position": Teacher.Position.DOCENTE_TITULADO,
    }

    response = logged_in_client.post(
        reverse("teacher-list"), payload, content_type="application/json"
    )

    assert response.status_code == 400
    detail = response.json()["error"]["detail"]
    assert "person" in detail
    assert "first_name" in detail["person"]
    assert "last_name" in detail["person"]


@pytest.mark.api
@pytest.mark.django_db
def test_list_teachers_is_paginated(logged_in_client):
    TeacherFactory.create_batch(3)

    response = logged_in_client.get(reverse("teacher-list"))

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] == Teacher.objects.count()


@pytest.mark.api
@pytest.mark.django_db
def test_list_teachers_returns_nested_person(logged_in_client):
    teacher = TeacherFactory()

    response = logged_in_client.get(reverse("teacher-list"))

    assert response.status_code == 200
    results = response.json()["results"]
    match = next(item for item in results if item["id"] == teacher.pk)
    assert isinstance(match["person"], dict)
    assert match["person"]["first_name"] == teacher.person.first_name
    assert match["person"]["last_name"] == teacher.person.last_name


@pytest.mark.api
@pytest.mark.django_db
def test_upload_teacher_photo(logged_in_client):
    teacher = TeacherFactory()
    photo = SimpleUploadedFile("photo.jpg", b"fake-image-bytes", content_type="image/jpeg")

    response = logged_in_client.patch(
        reverse("teacher-detail", args=[teacher.pk]),
        data=encode_multipart(BOUNDARY, {"photo": photo}),
        content_type=MULTIPART_CONTENT,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["photo"]
    teacher.refresh_from_db()
    assert teacher.photo.name


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_teacher(logged_in_client):
    teacher = TeacherFactory()

    response = logged_in_client.get(reverse("teacher-detail", args=[teacher.pk]))

    assert response.status_code == 200
    assert response.json()["id"] == teacher.pk


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_missing_teacher_returns_404(logged_in_client):
    response = logged_in_client.get(reverse("teacher-detail", args=[999999]))

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_update_teacher(logged_in_client):
    teacher = TeacherFactory(position=Teacher.Position.DOCENTE_INTERINO)

    response = logged_in_client.patch(
        reverse("teacher-detail", args=[teacher.pk]),
        {"position": Teacher.Position.DOCENTE_TITULADO},
        content_type="application/json",
    )

    assert response.status_code == 200
    teacher.refresh_from_db()
    assert teacher.position == Teacher.Position.DOCENTE_TITULADO


@pytest.mark.api
@pytest.mark.django_db
def test_deactivate_teacher_via_delete_is_soft(logged_in_client):
    teacher = TeacherFactory()

    response = logged_in_client.delete(reverse("teacher-detail", args=[teacher.pk]))

    assert response.status_code == 204
    teacher.refresh_from_db()
    assert teacher.is_active is False
    assert Teacher.objects.filter(pk=teacher.pk).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_create_teacher_duplicate_employee_code_is_rejected(logged_in_client):
    existing = TeacherFactory(employee_code="EMP-2000")
    person_count = Person.objects.count()

    response = logged_in_client.post(
        reverse("teacher-list"),
        {
            "person": {"first_name": "Ana", "last_name": "Ramirez"},
            "employee_code": existing.employee_code,
            "specialty": "Matematica",
            "position": Teacher.Position.DOCENTE_TITULADO,
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    detail = response.json()["error"]["detail"]
    assert "employee_code" in detail
    assert Person.objects.count() == person_count


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_is_rejected(client):
    response = client.get(reverse("teacher-list"))

    assert response.status_code == 403
