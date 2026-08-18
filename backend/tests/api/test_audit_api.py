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
from tests.factories.identity import UserFactory

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
    assert event.context["changes"]["name"] == {"before": "Old", "after": "New"}


def test_deactivating_a_resource_via_the_api_is_audited(auth_client, institution):
    template = DocumentTemplateFactory(institution=institution)

    response = auth_client.delete(reverse("document-template-detail", args=[template.public_id]))

    assert response.status_code == 204
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "documents.template.deactivated"


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
