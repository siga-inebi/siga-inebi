import uuid

import pytest
from django.urls import reverse

from apps.students.models import EmergencyContact
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.students import EmergencyContactFactory, StudentFactory


@pytest.fixture
def logged_in_client(client):
    user = UserFactory(password="test-pass-123")
    client.login(username=user.username, password="test-pass-123")
    client.test_user = user
    return client


def grant_contact_access(client, student):
    grant(client.test_user, student, "student_view_sensitive", "student_edit_basic")


@pytest.mark.api
@pytest.mark.django_db
def test_create_emergency_contact(logged_in_client):
    student = StudentFactory()
    grant_contact_access(logged_in_client, student)

    response = logged_in_client.post(
        reverse("student-emergency-contact-list-create", args=[student.public_id]),
        {
            "name": "Maria Perez",
            "phone_number": "555-0123",
            "relationship_label": "Tia",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["student"]["public_id"] == str(student.public_id)
    assert data["name"] == "Maria Perez"
    assert data["phone_number"] == "555-0123"
    assert data["relationship_label"] == "Tia"
    assert data["is_active"] is True
    assert "id" not in data
    assert EmergencyContact.objects.filter(public_id=data["public_id"]).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_create_emergency_contact_under_unknown_student_returns_404(logged_in_client):
    response = logged_in_client.post(
        reverse("student-emergency-contact-list-create", args=[uuid.uuid4()]),
        {
            "name": "Maria Perez",
            "phone_number": "555-0123",
            "relationship_label": "Tia",
        },
    )

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_create_emergency_contact_under_inactive_student_is_rejected(logged_in_client):
    student = StudentFactory(is_active=False)
    grant_contact_access(logged_in_client, student)

    response = logged_in_client.post(
        reverse("student-emergency-contact-list-create", args=[student.public_id]),
        {
            "name": "Maria Perez",
            "phone_number": "555-0123",
            "relationship_label": "Tia",
        },
    )

    assert response.status_code == 400


@pytest.mark.api
@pytest.mark.django_db
def test_list_emergency_contacts_is_paginated_and_scoped_to_student(logged_in_client):
    student = StudentFactory()
    grant_contact_access(logged_in_client, student)
    EmergencyContactFactory.create_batch(3, student=student)
    EmergencyContactFactory.create_batch(2)  # other students, must not leak into the list

    response = logged_in_client.get(
        reverse("student-emergency-contact-list-create", args=[student.public_id])
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] == 3


@pytest.mark.api
@pytest.mark.django_db
def test_list_emergency_contacts_hides_inactive_unless_requested(logged_in_client):
    student = StudentFactory()
    grant_contact_access(logged_in_client, student)
    EmergencyContactFactory(student=student, is_active=False)
    EmergencyContactFactory(student=student, is_active=True)
    list_url = reverse("student-emergency-contact-list-create", args=[student.public_id])

    response = logged_in_client.get(list_url)
    assert response.json()["count"] == 1

    response = logged_in_client.get(list_url, {"include_inactive": "true"})
    assert response.json()["count"] == 2


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_emergency_contact(logged_in_client):
    contact = EmergencyContactFactory()
    grant_contact_access(logged_in_client, contact.student)

    response = logged_in_client.get(reverse("emergency-contact-detail", args=[contact.public_id]))

    assert response.status_code == 200
    assert response.json()["public_id"] == str(contact.public_id)


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_missing_emergency_contact_returns_404(logged_in_client):
    response = logged_in_client.get(reverse("emergency-contact-detail", args=[uuid.uuid4()]))

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_update_emergency_contact(logged_in_client):
    contact = EmergencyContactFactory(name="Old Name")
    grant_contact_access(logged_in_client, contact.student)

    response = logged_in_client.patch(
        reverse("emergency-contact-detail", args=[contact.public_id]),
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
    grant_contact_access(logged_in_client, contact.student)

    response = logged_in_client.delete(
        reverse("emergency-contact-detail", args=[contact.public_id])
    )

    assert response.status_code == 204
    contact.refresh_from_db()
    assert contact.is_active is False
    assert EmergencyContact.objects.filter(pk=contact.pk).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_to_emergency_contact_list_is_rejected(client):
    student = StudentFactory()

    response = client.get(
        reverse("student-emergency-contact-list-create", args=[student.public_id])
    )

    assert response.status_code == 403


def grant(user, student, *codenames):
    permissions = [PermissionFactory(codename=codename) for codename in codenames]
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=permissions))
    ScopeGrantFactory(assignment=assignment, student=student)


@pytest.mark.api
@pytest.mark.django_db
def test_contact_access_requires_sensitive_permission_and_student_scope(client):
    user = UserFactory(password="test-pass-123")
    client.login(username=user.username, password="test-pass-123")
    allowed_student = StudentFactory()
    denied_student = StudentFactory()
    grant(user, allowed_student, "student_view_sensitive", "student_edit_basic")

    assert (
        client.get(
            reverse("student-emergency-contact-list-create", args=[denied_student.public_id])
        ).status_code
        == 403
    )
    assert (
        client.post(
            reverse("student-emergency-contact-list-create", args=[denied_student.public_id]),
            {"name": "No permitido", "phone_number": "555-0000", "relationship_label": "Otro"},
        ).status_code
        == 403
    )
