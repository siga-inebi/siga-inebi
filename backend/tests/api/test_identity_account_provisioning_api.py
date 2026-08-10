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


def provision_pending_account(client, *, username="account-to-activate"):
    client.force_login(UserFactory(is_superuser=True))
    response = client.post(
        reverse("identity-account-provision"),
        {"person": PersonFactory().pk, "username": username},
    )
    assert response.status_code == 201
    client.logout()
    return response.json()


@pytest.mark.api
@pytest.mark.security
@pytest.mark.postgres
@pytest.mark.django_db
def test_account_holder_redeems_code_sets_password_and_activates_account(client):
    provisioned = provision_pending_account(client)

    response = client.post(
        reverse("identity-account-activate"),
        {
            "username": provisioned["username"],
            "activation_code": provisioned["activation_code"],
            "password": "long-password-not-common-427",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    account = UserFactory._meta.model.objects.get(pk=provisioned["id"])
    assert account.is_active is True
    assert account.check_password("long-password-not-common-427")
    challenge = ActivationChallenge.objects.get(account=account)
    assert challenge.used_at is not None
    assert challenge.is_active is False
    event = AuditEvent.objects.get(action="identity.account.activated")
    assert event.actor == account
    assert event.context["challenge_id"] == str(challenge.public_id)
    assert "password" not in str(event.context).lower()


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_redeemed_code_cannot_be_used_again(client):
    provisioned = provision_pending_account(client, username="single-use-account")
    payload = {
        "username": provisioned["username"],
        "activation_code": provisioned["activation_code"],
        "password": "first-long-password-427",
    }
    assert client.post(reverse("identity-account-activate"), payload).status_code == 200

    payload["password"] = "second-long-password-427"
    response = client.post(reverse("identity-account-activate"), payload)

    assert response.status_code == 400
    account = UserFactory._meta.model.objects.get(pk=provisioned["id"])
    assert account.check_password("first-long-password-427")
    assert not account.check_password("second-long-password-427")


@pytest.mark.api
@pytest.mark.security
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(ACCOUNT_ACTIVATION_MAX_ATTEMPTS=3)
def test_three_invalid_codes_exhaust_challenge_and_attempts_are_audited(client):
    provisioned = provision_pending_account(client, username="attempt-limited-account")
    url = reverse("identity-account-activate")
    invalid_payload = {
        "username": provisioned["username"],
        "activation_code": "00000000",
        "password": "long-password-not-common-427",
    }

    for expected_attempts in range(1, 4):
        response = client.post(url, invalid_payload)
        assert response.status_code == 400
        challenge = ActivationChallenge.objects.get(account_id=provisioned["id"])
        assert challenge.failed_attempts == expected_attempts

    valid_response = client.post(
        url,
        {**invalid_payload, "activation_code": provisioned["activation_code"]},
    )
    assert valid_response.status_code == 400
    account = UserFactory._meta.model.objects.get(pk=provisioned["id"])
    assert account.status == "pending"
    assert account.is_active is False
    assert (
        AuditEvent.objects.filter(
            action="identity.activation_challenge.denied",
            context__reason="invalid_code",
        ).count()
        == 3
    )


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_expired_code_does_not_activate_account(client):
    provisioned = provision_pending_account(client, username="expired-code-account")
    challenge = ActivationChallenge.objects.get(account_id=provisioned["id"])
    challenge.expires_at = timezone.now() - timedelta(seconds=1)
    challenge.save(update_fields=["expires_at"])

    response = client.post(
        reverse("identity-account-activate"),
        {
            "username": provisioned["username"],
            "activation_code": provisioned["activation_code"],
            "password": "long-password-not-common-427",
        },
    )

    assert response.status_code == 400
    event = AuditEvent.objects.filter(action="identity.activation_challenge.denied").latest(
        "created_at"
    )
    assert event.context["reason"] == "expired"


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_password_policy_rejection_preserves_usable_challenge(client):
    provisioned = provision_pending_account(client, username="password-policy-account")

    response = client.post(
        reverse("identity-account-activate"),
        {
            "username": provisioned["username"],
            "activation_code": provisioned["activation_code"],
            "password": "password",
        },
    )

    assert response.status_code == 400
    challenge = ActivationChallenge.objects.get(account_id=provisioned["id"])
    assert challenge.is_usable()
    assert challenge.failed_attempts == 0
    account = UserFactory._meta.model.objects.get(pk=provisioned["id"])
    assert account.status == "pending"
    assert account.is_active is False
    event = AuditEvent.objects.filter(action="identity.activation_challenge.denied").latest(
        "created_at"
    )
    assert event.context["reason"] == "password_policy"


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_unknown_account_and_invalid_code_share_public_error(client):
    provisioned = provision_pending_account(client, username="uniform-error-account")
    url = reverse("identity-account-activate")
    password = "long-password-not-common-427"

    unknown = client.post(
        url,
        {"username": "does-not-exist", "activation_code": "00000000", "password": password},
    )
    invalid = client.post(
        url,
        {
            "username": provisioned["username"],
            "activation_code": "00000000",
            "password": password,
        },
    )

    assert unknown.status_code == invalid.status_code == 400
    assert unknown.json() == invalid.json()
