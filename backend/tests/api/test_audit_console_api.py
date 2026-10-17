"""
docs/ux-ui.md AU1: la consola de bitacora filtra por usuario (sin id interno),
por prefijo de accion y exporta el rango completo, sin truncar.
"""

import csv
import io

import pytest
from django.urls import reverse

from apps.audit.services import record_event
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]


@pytest.fixture
def auditor(client):
    user = UserFactory(username="auditora")
    RoleAssignmentFactory(
        user=user, role=RoleFactory(permissions=[PermissionFactory(codename="audit_read")])
    )
    client.force_login(user)
    client.user = user
    return client


def test_events_filter_by_actor_username_and_public_id(auditor):
    ana = UserFactory(username="ana.lopez")
    other = UserFactory(username="otro")
    record_event(actor=ana, action="identity.account.updated", resource="UserAccount")
    record_event(actor=other, action="identity.account.updated", resource="UserAccount")

    by_username = auditor.get(reverse("audit-event-list"), {"actor_username": "ana."}).json()
    by_public_id = auditor.get(
        reverse("audit-event-list"), {"actor_public_id": str(ana.public_id)}
    ).json()

    assert [row["actor_label"] for row in by_username["results"]] == ["ana.lopez"]
    assert by_public_id["results"][0]["actor_public_id"] == str(ana.public_id)
    assert by_public_id["count"] == 1


def test_events_filter_by_action_prefix(auditor):
    actor = UserFactory()
    record_event(actor=actor, action="identity.account.unlocked", resource="UserAccount")
    record_event(actor=actor, action="documents.template.created", resource="DocumentTemplate")

    payload = auditor.get(reverse("audit-event-list"), {"action_prefix": "identity.account"}).json()

    assert {row["action"] for row in payload["results"]} == {"identity.account.unlocked"}


def test_export_contains_every_matching_event_without_truncation(auditor):
    actor = UserFactory()
    for index in range(130):
        record_event(actor=actor, action="test.bulk.event", resource=f"R{index}")

    response = auditor.get(reverse("audit-event-export"), {"action": "test.bulk.event"})

    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.content.decode())))
    assert len(rows) == 131  # encabezado + 130, mas de una pagina de 100


def test_events_require_audit_permission(client):
    client.force_login(UserFactory())

    assert client.get(reverse("audit-event-list")).status_code == 403
