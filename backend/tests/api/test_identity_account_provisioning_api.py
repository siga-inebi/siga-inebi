from datetime import timedelta

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.identity.models import ActivationChallenge
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.people import PersonFactory


def grant_permission(user, codename):
    permission = PermissionFactory(codename=codename)
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


@pytest.mark.api
@pytest.mark.security
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(ACCOUNT_ACTIVATION_TTL_MINUTES=15, ACCOUNT_ACTIVATION_MAX_ATTEMPTS=3)
def test_administrator_provisions_pending_account_and_receives_code_once(client):
    actor = UserFactory()
    grant_permission(actor, "account_create")
    client.force_login(actor)
    person = PersonFactory(email="new.user@example.test")

    response = client.post(
        reverse("identity-account-provision"),
        {"person": person.pk, "username": "new.user"},
    )

    assert response.status_code == 201
    assert response["Cache-Control"] == "no-store"
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["person"] == person.pk
    assert payload["activation_code"].isdigit()
    assert len(payload["activation_code"]) == 8

    challenge = ActivationChallenge.objects.get(account_id=payload["id"])
    assert challenge.token_digest != payload["activation_code"]
    assert len(challenge.token_digest) == 64
    assert challenge.failed_attempts == 0
    assert timedelta(minutes=14, seconds=55) <= challenge.expires_at - timezone.now()
    assert challenge.is_usable()

    for event in AuditEvent.objects.all():
        assert payload["activation_code"] not in str(event.context)


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_account_provisioning_requires_account_create_permission(client):
    actor = UserFactory()
    client.force_login(actor)
    person = PersonFactory()

    response = client.post(
        reverse("identity-account-provision"),
        {"person": person.pk, "username": "not-created"},
    )

    assert response.status_code == 403
    assert not hasattr(person, "user_account")
    event = AuditEvent.objects.get(action="identity.account.create_denied")
    assert event.context["person_id"] == person.pk


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_account_provisioning_requires_authentication(client):
    person = PersonFactory()

    response = client.post(
        reverse("identity-account-provision"),
        {"person": person.pk, "username": "anonymous-account"},
    )

    assert response.status_code == 403


@pytest.mark.api
@pytest.mark.security
@pytest.mark.postgres
@pytest.mark.django_db
def test_authorized_administrator_reissues_and_revokes_previous_challenge(client):
    creator = UserFactory(is_superuser=True)
    person = PersonFactory()
    client.force_login(creator)
    initial_response = client.post(
        reverse("identity-account-provision"),
        {"person": person.pk, "username": "pending-account"},
    )
    account_id = initial_response.json()["id"]
    old_code = initial_response.json()["activation_code"]
    previous = ActivationChallenge.objects.get(account_id=account_id)

    actor = UserFactory()
    grant_permission(actor, "account_activate")
    client.force_login(actor)
    response = client.post(
        reverse("identity-activation-challenge-reissue", args=[account_id]),
    )

    assert response.status_code == 201
    assert response["Cache-Control"] == "no-store"
    assert response.json()["activation_code"] != old_code
    assert response.json()["max_attempts"] == 3
    previous.refresh_from_db()
    assert previous.is_active is False
    assert previous.revoked_at is not None
    assert previous.is_usable() is False
    assert ActivationChallenge.objects.filter(account_id=account_id).count() == 2


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_reissue_requires_account_activate_permission(client):
    account = UserFactory(status="pending", is_active=False)
    actor = UserFactory()
    client.force_login(actor)

    response = client.post(
        reverse("identity-activation-challenge-reissue", args=[account.pk]),
    )

    assert response.status_code == 403
    event = AuditEvent.objects.get(action="identity.activation_challenge.issue_denied")
    assert event.context["target_user_id"] == account.pk


@pytest.mark.unit
@pytest.mark.django_db
@override_settings(ACCOUNT_ACTIVATION_MAX_ATTEMPTS=3)
def test_challenge_is_not_usable_after_three_failed_attempts():
    challenge = ActivationChallenge.objects.create(
        account=UserFactory(status="pending", is_active=False),
        token_digest="a" * 64,
        expires_at=timezone.now() + timedelta(minutes=15),
        failed_attempts=3,
    )

    assert challenge.is_usable() is False
