import pytest
from django.urls import reverse

from apps.students.models import Guardian
from tests.factories.identity import UserFactory
from tests.factories.people import PersonFactory
from tests.factories.students import GuardianFactory


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
def test_guardian_options_lists_only_active_guardians_unpaginated(logged_in_client):
    GuardianFactory.create_batch(2)
    GuardianFactory(is_active=False)

    response = logged_in_client.get(reverse("guardian-option-list"))

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert all("public_id" in item and "person" in item for item in data)


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_to_guardian_options_is_rejected(client):
    response = client.get(reverse("guardian-option-list"))

    assert response.status_code == 403
