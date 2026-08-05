import pytest
from django.urls import reverse
from django.utils import timezone

from apps.students.models import Guardian, StudentGuardianRelation
from tests.factories.identity import UserFactory
from tests.factories.people import PersonFactory
from tests.factories.students import (
    GuardianFactory,
    StudentFactory,
    StudentGuardianRelationFactory,
)


@pytest.fixture
def logged_in_client(client):
    user = UserFactory(password="test-pass-123")
    client.login(username=user.username, password="test-pass-123")
    return client


@pytest.mark.api
@pytest.mark.django_db
def test_create_guardian(logged_in_client):
    person = PersonFactory()

    response = logged_in_client.post(reverse("guardian-list"), {"person": person.pk})

    assert response.status_code == 201
    data = response.json()
    assert data["person"] == person.pk
    assert data["is_active"] is True
    assert Guardian.objects.filter(pk=data["id"]).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_list_guardians_is_paginated(logged_in_client):
    GuardianFactory.create_batch(3)

    response = logged_in_client.get(reverse("guardian-list"))

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] == Guardian.objects.count()


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_guardian(logged_in_client):
    guardian = GuardianFactory()

    response = logged_in_client.get(reverse("guardian-detail", args=[guardian.pk]))

    assert response.status_code == 200
    assert response.json()["id"] == guardian.pk


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_missing_guardian_returns_404(logged_in_client):
    response = logged_in_client.get(reverse("guardian-detail", args=[999999]))

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_update_guardian(logged_in_client):
    guardian = GuardianFactory()
    other_person = PersonFactory()

    response = logged_in_client.patch(
        reverse("guardian-detail", args=[guardian.pk]),
        {"person": other_person.pk},
        content_type="application/json",
    )

    assert response.status_code == 200
    guardian.refresh_from_db()
    assert guardian.person_id == other_person.pk


@pytest.mark.api
@pytest.mark.django_db
def test_deactivate_guardian_via_delete_is_soft(logged_in_client):
    guardian = GuardianFactory()

    response = logged_in_client.delete(reverse("guardian-detail", args=[guardian.pk]))

    assert response.status_code == 204
    guardian.refresh_from_db()
    assert guardian.is_active is False
    assert Guardian.objects.filter(pk=guardian.pk).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_create_guardian_duplicate_person_is_rejected(logged_in_client):
    existing = GuardianFactory()

    response = logged_in_client.post(reverse("guardian-list"), {"person": existing.person_id})

    assert response.status_code == 400
    detail = response.json()["error"]["detail"]
    assert "person" in detail


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_to_guardian_list_is_rejected(client):
    response = client.get(reverse("guardian-list"))

    assert response.status_code == 403


@pytest.mark.api
@pytest.mark.django_db
def test_create_student_guardian_relation(logged_in_client):
    student = StudentFactory()
    guardian = GuardianFactory()

    response = logged_in_client.post(
        reverse("student-guardian-relation-list"),
        {
            "student": student.pk,
            "guardian": guardian.pk,
            "relationship_label": "Madre",
            "is_primary": True,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["student"] == student.pk
    assert data["guardian"] == guardian.pk
    assert data["relationship_label"] == "Madre"
    assert data["is_primary"] is True
    assert data["ends_at"] is None
    assert StudentGuardianRelation.objects.filter(pk=data["id"]).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_list_student_guardian_relations_is_paginated(logged_in_client):
    StudentGuardianRelationFactory.create_batch(3)

    response = logged_in_client.get(reverse("student-guardian-relation-list"))

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] == StudentGuardianRelation.objects.count()


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_student_guardian_relation(logged_in_client):
    relation = StudentGuardianRelationFactory()

    response = logged_in_client.get(reverse("student-guardian-relation-detail", args=[relation.pk]))

    assert response.status_code == 200
    assert response.json()["id"] == relation.pk


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_missing_student_guardian_relation_returns_404(logged_in_client):
    response = logged_in_client.get(reverse("student-guardian-relation-detail", args=[999999]))

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_update_student_guardian_relation(logged_in_client):
    relation = StudentGuardianRelationFactory(relationship_label="Padre")

    response = logged_in_client.patch(
        reverse("student-guardian-relation-detail", args=[relation.pk]),
        {"relationship_label": "Tutor"},
        content_type="application/json",
    )

    assert response.status_code == 200
    relation.refresh_from_db()
    assert relation.relationship_label == "Tutor"


@pytest.mark.api
@pytest.mark.django_db
def test_ending_student_guardian_relation_via_delete_sets_ends_at(logged_in_client):
    relation = StudentGuardianRelationFactory(ends_at=None)

    response = logged_in_client.delete(
        reverse("student-guardian-relation-detail", args=[relation.pk])
    )

    assert response.status_code == 204
    relation.refresh_from_db()
    assert relation.ends_at == timezone.localdate()
    assert StudentGuardianRelation.objects.filter(pk=relation.pk).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_create_student_guardian_relation_missing_student_is_rejected(logged_in_client):
    guardian = GuardianFactory()

    response = logged_in_client.post(
        reverse("student-guardian-relation-list"),
        {
            "student": 999999,
            "guardian": guardian.pk,
            "relationship_label": "Madre",
        },
    )

    assert response.status_code == 400
    detail = response.json()["error"]["detail"]
    assert "student" in detail


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_to_relation_list_is_rejected(client):
    response = client.get(reverse("student-guardian-relation-list"))

    assert response.status_code == 403
