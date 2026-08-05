import pytest
from django.urls import reverse

from apps.students.models import EmergencyContact
from tests.factories.identity import UserFactory
from tests.factories.students import EmergencyContactFactory, StudentFactory


@pytest.fixture
def logged_in_client(client):
    user = UserFactory(password="test-pass-123")
    client.login(username=user.username, password="test-pass-123")
    return client


@pytest.mark.api
@pytest.mark.django_db
def test_create_emergency_contact(logged_in_client):
    student = StudentFactory()

    response = logged_in_client.post(
        reverse("emergency-contact-list"),
        {
            "student": student.pk,
            "name": "Maria Perez",
            "phone_number": "555-0123",
            "relationship_label": "Tia",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["student"] == student.pk
    assert data["name"] == "Maria Perez"
    assert data["phone_number"] == "555-0123"
    assert data["relationship_label"] == "Tia"
    assert data["is_active"] is True
    assert EmergencyContact.objects.filter(pk=data["id"]).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_list_emergency_contacts_is_paginated(logged_in_client):
    EmergencyContactFactory.create_batch(3)

    response = logged_in_client.get(reverse("emergency-contact-list"))

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] == EmergencyContact.objects.count()


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_emergency_contact(logged_in_client):
    contact = EmergencyContactFactory()

    response = logged_in_client.get(reverse("emergency-contact-detail", args=[contact.pk]))

    assert response.status_code == 200
    assert response.json()["id"] == contact.pk


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_missing_emergency_contact_returns_404(logged_in_client):
    response = logged_in_client.get(reverse("emergency-contact-detail", args=[999999]))

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_update_emergency_contact(logged_in_client):
    contact = EmergencyContactFactory(name="Old Name")

    response = logged_in_client.patch(
        reverse("emergency-contact-detail", args=[contact.pk]),
        {"name": "New Name"},
        content_type="application/json",
    )

    assert response.status_code == 200
    contact.refresh_from_db()
    assert contact.name == "New Name"


@pytest.mark.api
@pytest.mark.django_db
def test_deactivate_emergency_contact_via_delete_is_soft(logged_in_client):
    contact = EmergencyContactFactory()

    response = logged_in_client.delete(reverse("emergency-contact-detail", args=[contact.pk]))

    assert response.status_code == 204
    contact.refresh_from_db()
    assert contact.is_active is False
    assert EmergencyContact.objects.filter(pk=contact.pk).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_create_emergency_contact_missing_student_is_rejected(logged_in_client):
    response = logged_in_client.post(
        reverse("emergency-contact-list"),
        {
            "student": 999999,
            "name": "Maria Perez",
            "phone_number": "555-0123",
            "relationship_label": "Tia",
        },
    )

    assert response.status_code == 400
    detail = response.json()["error"]["detail"]
    assert "student" in detail


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_to_emergency_contact_list_is_rejected(client):
    response = client.get(reverse("emergency-contact-list"))

    assert response.status_code == 403
