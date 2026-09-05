import uuid
from datetime import date

import pytest
from django.urls import reverse

from apps.people.models import Person
from tests.factories.identity import UserFactory
from tests.factories.people import PersonFactory


@pytest.fixture
def logged_in_client(client):
    user = UserFactory(password="test-pass-123")
    client.login(username=user.username, password="test-pass-123")
    return client


@pytest.mark.api
@pytest.mark.django_db
def test_create_person(logged_in_client):
    payload = {
        "first_name": "Ana",
        "last_name": "Gomez",
        "email": "ana.gomez@example.test",
        "phone_number": "5551234567",
        "institutional_identifier": "INEBI-001",
    }

    response = logged_in_client.post(reverse("person-list"), payload)

    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Ana"
    assert data["is_active"] is True
    assert "id" not in data
    assert Person.objects.filter(public_id=data["public_id"]).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_create_person_requires_first_and_last_name(logged_in_client):
    response = logged_in_client.post(reverse("person-list"), {})

    assert response.status_code == 400
    detail = response.json()["error"]["detail"]
    assert "first_name" in detail
    assert "last_name" in detail


@pytest.mark.api
@pytest.mark.django_db
def test_list_people_is_paginated(logged_in_client):
    PersonFactory.create_batch(3)

    response = logged_in_client.get(reverse("person-list"))

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] == Person.objects.count()


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_person(logged_in_client):
    person = PersonFactory()

    response = logged_in_client.get(reverse("person-detail", args=[person.public_id]))

    assert response.status_code == 200
    assert response.json()["public_id"] == str(person.public_id)


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_missing_person_returns_404(logged_in_client):
    response = logged_in_client.get(reverse("person-detail", args=[uuid.uuid4()]))

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_update_person(logged_in_client):
    person = PersonFactory(first_name="Old")

    response = logged_in_client.patch(
        reverse("person-detail", args=[person.public_id]),
        {"first_name": "New"},
        content_type="application/json",
    )

    assert response.status_code == 200
    person.refresh_from_db()
    assert person.first_name == "New"


@pytest.mark.api
@pytest.mark.django_db
def test_deactivate_person_via_delete_is_soft(logged_in_client):
    person = PersonFactory()

    response = logged_in_client.delete(reverse("person-detail", args=[person.public_id]))

    assert response.status_code == 204
    person.refresh_from_db()
    assert person.is_active is False
    assert Person.objects.filter(pk=person.pk).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_is_rejected(client):
    response = client.get(reverse("person-list"))

    assert response.status_code == 403


@pytest.mark.api
@pytest.mark.django_db
def test_create_person_never_exposes_birth_date(logged_in_client):
    payload = {
        "first_name": "Ana",
        "last_name": "Gomez",
        "birth_date": "2015-03-01",
    }

    response = logged_in_client.post(reverse("person-list"), payload)

    assert response.status_code == 201
    data = response.json()
    assert "birth_date" not in data
    assert data["is_minor"] is True
    person = Person.objects.get(public_id=data["public_id"])
    assert person.birth_date == date(2015, 3, 1)


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_person_never_exposes_birth_date(logged_in_client):
    person = PersonFactory(birth_date=date(1990, 1, 1))

    response = logged_in_client.get(reverse("person-detail", args=[person.public_id]))

    assert response.status_code == 200
    data = response.json()
    assert "birth_date" not in data
    assert data["is_minor"] is False
