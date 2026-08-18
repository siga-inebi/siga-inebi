"""
End-to-end proof that write operations are audited through the real HTTP
contract, not just when a service is called directly (RF-BIT-001). Uses the
``documents`` endpoints (RF-PLA-001) as the vehicle: stable, already covers
create/update/deactivate in one place.
"""

import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from tests.factories.documents import DocumentTemplateFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_creating_a_resource_via_the_api_is_audited(auth_client, institution):
    response = auth_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia", "code": "CONST"},
        content_type="application/json",
    )

    assert response.status_code == 201
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "documents.template.created"
    assert event.actor_id == auth_client.user.id


def test_updating_a_resource_via_the_api_is_audited(auth_client, institution):
    template = DocumentTemplateFactory(institution=institution, name="Old")

    response = auth_client.patch(
        reverse("document-template-detail", args=[template.public_id]),
        {"name": "New"},
        content_type="application/json",
    )

    assert response.status_code == 200
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "documents.template.updated"
    assert event.resource_identifier == str(template.pk)


def test_deactivating_a_resource_via_the_api_is_audited(auth_client, institution):
    template = DocumentTemplateFactory(institution=institution)

    response = auth_client.delete(reverse("document-template-detail", args=[template.public_id]))

    assert response.status_code == 204
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "documents.template.deactivated"


def test_reading_a_students_family_contacts_via_the_api_is_audited(auth_client):
    """RF-BIT-003: consulting one identified student's family contact data is a sensitive read."""
    student = StudentFactory()

    response = auth_client.get(
        reverse("student-emergency-contact-list-create", args=[student.public_id])
    )

    assert response.status_code == 200
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "students.emergency_contacts.read"
    assert event.context["student_id"] == student.pk
    assert event.actor_id == auth_client.user.id
