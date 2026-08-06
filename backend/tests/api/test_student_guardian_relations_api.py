import uuid

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.students.models import StudentGuardianRelation
from tests.factories.identity import UserFactory
from tests.factories.students import GuardianFactory, StudentFactory, StudentGuardianRelationFactory


@pytest.fixture
def logged_in_client(client):
    user = UserFactory(password="test-pass-123")
    client.login(username=user.username, password="test-pass-123")
    return client


def _list_url(student):
    return reverse("student-guardian-relation-list-create", args=[student.public_id])


def _detail_url(relation):
    return reverse("student-guardian-relation-detail", args=[relation.public_id])


@pytest.mark.api
@pytest.mark.django_db
def test_create_student_guardian_relation(logged_in_client):
    student = StudentFactory()
    guardian = GuardianFactory()

    response = logged_in_client.post(
        _list_url(student),
        {
            "guardian_id": str(guardian.public_id),
            "relationship_label": "Madre",
            "is_primary": True,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["student"]["public_id"] == str(student.public_id)
    assert data["guardian"]["public_id"] == str(guardian.public_id)
    assert data["relationship_label"] == "Madre"
    assert data["is_primary"] is True
    assert data["ends_at"] is None
    assert "id" not in data
    assert StudentGuardianRelation.objects.filter(public_id=data["public_id"]).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_create_relation_under_unknown_student_returns_404(logged_in_client):
    guardian = GuardianFactory()

    response = logged_in_client.post(
        reverse("student-guardian-relation-list-create", args=[uuid.uuid4()]),
        {"guardian_id": str(guardian.public_id), "relationship_label": "Madre"},
    )

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_create_relation_with_unknown_guardian_is_rejected(logged_in_client):
    student = StudentFactory()

    response = logged_in_client.post(
        _list_url(student),
        {"guardian_id": str(uuid.uuid4()), "relationship_label": "Madre"},
    )

    assert response.status_code == 400


@pytest.mark.api
@pytest.mark.django_db
def test_create_relation_under_inactive_student_is_rejected(logged_in_client):
    student = StudentFactory(is_active=False)
    guardian = GuardianFactory()

    response = logged_in_client.post(
        _list_url(student),
        {"guardian_id": str(guardian.public_id), "relationship_label": "Madre"},
    )

    assert response.status_code == 400


@pytest.mark.api
@pytest.mark.django_db
def test_create_relation_with_inactive_guardian_is_rejected(logged_in_client):
    student = StudentFactory()
    guardian = GuardianFactory(is_active=False)

    response = logged_in_client.post(
        _list_url(student),
        {"guardian_id": str(guardian.public_id), "relationship_label": "Madre"},
    )

    assert response.status_code == 400


@pytest.mark.api
@pytest.mark.django_db
def test_create_relation_rejects_duplicate_active_pairing(logged_in_client):
    student = StudentFactory()
    guardian = GuardianFactory()
    StudentGuardianRelationFactory(student=student, guardian=guardian)

    response = logged_in_client.post(
        _list_url(student),
        {"guardian_id": str(guardian.public_id), "relationship_label": "Tutor"},
    )

    assert response.status_code == 400


@pytest.mark.api
@pytest.mark.django_db
def test_creating_second_primary_demotes_previous(logged_in_client):
    student = StudentFactory()
    first_guardian = GuardianFactory()
    second_guardian = GuardianFactory()
    first = StudentGuardianRelationFactory(
        student=student, guardian=first_guardian, is_primary=True
    )

    response = logged_in_client.post(
        _list_url(student),
        {
            "guardian_id": str(second_guardian.public_id),
            "relationship_label": "Padre",
            "is_primary": True,
        },
    )

    assert response.status_code == 201
    first.refresh_from_db()
    assert first.is_primary is False
    assert response.json()["is_primary"] is True


@pytest.mark.api
@pytest.mark.django_db
def test_list_student_guardian_relations_is_paginated_and_scoped_to_student(logged_in_client):
    student = StudentFactory()
    StudentGuardianRelationFactory.create_batch(2, student=student)
    StudentGuardianRelationFactory()  # another student, must not leak into the list

    response = logged_in_client.get(_list_url(student))

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert data["count"] == 2


@pytest.mark.api
@pytest.mark.django_db
def test_list_student_guardian_relations_hides_ended_unless_requested(logged_in_client):
    student = StudentFactory()
    StudentGuardianRelationFactory(student=student, ends_at=timezone.localdate())
    StudentGuardianRelationFactory(student=student, ends_at=None)
    list_url = _list_url(student)

    response = logged_in_client.get(list_url)
    assert response.json()["count"] == 1

    response = logged_in_client.get(list_url, {"include_inactive": "true"})
    assert response.json()["count"] == 2


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_student_guardian_relation(logged_in_client):
    relation = StudentGuardianRelationFactory()

    response = logged_in_client.get(_detail_url(relation))

    assert response.status_code == 200
    assert response.json()["public_id"] == str(relation.public_id)


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_missing_student_guardian_relation_returns_404(logged_in_client):
    response = logged_in_client.get(
        reverse("student-guardian-relation-detail", args=[uuid.uuid4()])
    )

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_update_student_guardian_relation(logged_in_client):
    relation = StudentGuardianRelationFactory(relationship_label="Padre")

    response = logged_in_client.patch(
        _detail_url(relation),
        {"relationship_label": "Tutor"},
        content_type="application/json",
    )

    assert response.status_code == 200
    relation.refresh_from_db()
    assert relation.relationship_label == "Tutor"


@pytest.mark.api
@pytest.mark.django_db
def test_promoting_is_primary_via_update_degrades_previous(logged_in_client):
    student = StudentFactory()
    primary = StudentGuardianRelationFactory(student=student, is_primary=True)
    candidate = StudentGuardianRelationFactory(student=student, is_primary=False)

    response = logged_in_client.patch(
        _detail_url(candidate),
        {"is_primary": True},
        content_type="application/json",
    )

    assert response.status_code == 200
    primary.refresh_from_db()
    assert primary.is_primary is False
    candidate.refresh_from_db()
    assert candidate.is_primary is True


@pytest.mark.api
@pytest.mark.django_db
def test_ending_student_guardian_relation_via_delete_sets_ends_at(logged_in_client):
    relation = StudentGuardianRelationFactory(ends_at=None)

    response = logged_in_client.delete(_detail_url(relation))

    assert response.status_code == 204
    relation.refresh_from_db()
    assert relation.ends_at == timezone.localdate()
    assert StudentGuardianRelation.objects.filter(pk=relation.pk).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_to_relation_list_is_rejected(client):
    student = StudentFactory()

    response = client.get(_list_url(student))

    assert response.status_code == 403
