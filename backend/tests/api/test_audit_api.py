"""
End-to-end proof that write operations are audited through the real HTTP
contract, not just when a service is called directly (RF-BIT-001). Uses the
``documents`` endpoints (RF-PLA-001) as the vehicle: stable, already covers
create/update/deactivate in one place.
"""

import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.identity.services import disable_account
from tests.factories.documents import DocumentTemplateFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _grant_audit_permission(user):
    permission = PermissionFactory(codename="audit_read")
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


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
    assert event.context["changes"]["name"] == {"before": "Old", "after": "New"}


def test_deactivating_a_resource_via_the_api_is_audited(auth_client, institution):
    template = DocumentTemplateFactory(institution=institution)

    response = auth_client.delete(reverse("document-template-detail", args=[template.public_id]))

    assert response.status_code == 204
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "documents.template.deactivated"


def test_listing_audit_events_via_the_api_is_filterable(auth_client, institution):
    """RF-BIT-006: restricted consulta, filterable by tipo de accion (among others)."""
    _grant_audit_permission(auth_client.user)
    auth_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia", "code": "CONST"},
        content_type="application/json",
    )

    response = auth_client.get(
        reverse("audit-event-list"), {"action": "documents.template.created"}
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["action"] == "documents.template.created"
    assert results[0]["actor_username"] == auth_client.user.username


def test_exporting_audit_events_via_the_api_generates_a_file_and_is_itself_audited(
    auth_client, institution
):
    """RF-BIT-006, Escenario 1: exportacion auditada."""
    _grant_audit_permission(auth_client.user)
    auth_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia", "code": "CONST"},
        content_type="application/json",
    )

    response = auth_client.get(reverse("audit-event-export"))

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    assert b"documents.template.created" in response.content

    export_event = AuditEvent.objects.latest("created_at")
    assert export_event.action == "audit.export.created"
    assert export_event.actor_id == auth_client.user.id
    assert export_event.context["count"] >= 1


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


def test_disabling_the_actor_does_not_alter_their_past_audit_events(auth_client, institution):
    """
    RF-BIT-007: attribution for a request made through the real API survives
    the actor's account being disabled afterwards.
    """
    response = auth_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia", "code": "CONST2"},
        content_type="application/json",
    )
    assert response.status_code == 201
    actor_id = auth_client.user.id
    actor_username = auth_client.user.username

    admin = UserFactory(is_superuser=True)
    disable_account(actor=admin, user=auth_client.user, force=True)

    event = AuditEvent.objects.get(action="documents.template.created", actor_id=actor_id)
    assert event.actor_id == actor_id
    assert event.actor_label == actor_username
