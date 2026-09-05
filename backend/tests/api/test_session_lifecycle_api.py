from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.identity.services import create_role, effective_session_idle_timeout_minutes
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.students import GuardianFactory


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.security
@pytest.mark.django_db
def test_operator_session_remains_open_inside_its_wider_role_timeout(client):
    user = UserFactory(password="session-pass-123")
    RoleAssignmentFactory(
        user=user,
        role=RoleFactory(session_idle_timeout_minutes=120),
    )
    client.force_login(user)
    session = client.session
    session["identity.session_last_activity_at"] = (
        timezone.now() - timedelta(minutes=20)
    ).isoformat()
    session.save()

    response = client.get(reverse("auth-me"))

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert not AuditEvent.objects.filter(action="identity.session.expired").exists()


@pytest.mark.unit
@pytest.mark.postgres
@pytest.mark.django_db
def test_effective_timeout_uses_the_largest_active_role_timeout():
    user = UserFactory()
    RoleAssignmentFactory(user=user, role=RoleFactory(session_idle_timeout_minutes=15))
    RoleAssignmentFactory(user=user, role=RoleFactory(session_idle_timeout_minutes=90))

    assert effective_session_idle_timeout_minutes(user=user) == 90


@pytest.mark.unit
@pytest.mark.postgres
@pytest.mark.django_db
def test_administrator_can_configure_a_role_idle_timeout():
    role = create_role(
        actor=UserFactory(is_superuser=True),
        name="Operador de control",
        slug="operador-control",
        session_idle_timeout_minutes=120,
    )

    assert role.session_idle_timeout_minutes == 120


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.security
@pytest.mark.django_db
def test_expired_administrative_session_is_denied_and_audited(client):
    user = UserFactory(password="session-pass-123")
    RoleAssignmentFactory(user=user, role=RoleFactory(session_idle_timeout_minutes=1))
    client.force_login(user)
    session = client.session
    session["identity.session_last_activity_at"] = (
        timezone.now() - timedelta(minutes=2)
    ).isoformat()
    session.save()

    response = client.get(reverse("auth-me"))

    assert response.status_code == 401
    assert response["X-SIGA-Session-Expired"] == "1"
    assert response.json()["error"]["detail"] == "La sesión expiró por inactividad."
    event = AuditEvent.objects.get(action="identity.session.expired")
    assert event.actor == user
    assert event.context["timeout_minutes"] == 1


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.security
@pytest.mark.django_db
def test_logout_current_session_is_audited(client):
    user = UserFactory()
    client.force_login(user)

    response = client.post(reverse("auth-logout"))

    assert response.status_code == 204
    assert "_auth_user_id" not in client.session
    event = AuditEvent.objects.get(action="identity.session.closed_current")
    assert event.actor == user


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.security
@pytest.mark.django_db
def test_account_holder_can_close_all_own_sessions(client):
    user = UserFactory()
    other_device = Client()
    client.force_login(user)
    other_device.force_login(user)

    response = client.post(reverse("auth-logout-all"))

    assert response.status_code == 204
    assert other_device.get(reverse("auth-me")).json()["authenticated"] is False
    event = AuditEvent.objects.get(action="identity.session.closed_all")
    assert event.actor == user
    assert event.context["closed_session_count"] >= 2


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.security
@pytest.mark.django_db
def test_authorized_administrator_can_close_another_accounts_sessions(client):
    administrator = UserFactory()
    permission = PermissionFactory(codename="account_disable")
    RoleAssignmentFactory(user=administrator, role=RoleFactory(permissions=[permission]))
    target = UserFactory()
    target_client = Client()
    target_client.force_login(target)
    client.force_login(administrator)

    response = client.post(reverse("identity-account-sessions-close", args=[target.pk]))

    assert response.status_code == 204
    assert target_client.get(reverse("auth-me")).json()["authenticated"] is False
    event = AuditEvent.objects.get(action="identity.session.closed_administratively")
    assert event.actor == administrator
    assert event.context["target_user_id"] == target.pk


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.security
@pytest.mark.django_db
def test_account_provision_rejects_orphan_and_unregistered_guardian(client):
    administrator = UserFactory(is_superuser=True)
    client.force_login(administrator)

    orphan_response = client.post(
        reverse("identity-account-provision"),
        {"username": "orphan-account"},
    )
    person = PersonFactory()
    guardian_response = client.post(
        reverse("identity-account-provision"),
        {"person": person.pk, "username": "guardian-account", "account_kind": "guardian"},
    )

    assert orphan_response.status_code == 400
    assert guardian_response.status_code == 400
    assert "registrarse primero como encargado" in guardian_response.json()["error"]["detail"]


@pytest.mark.unit
@pytest.mark.postgres
@pytest.mark.security
@pytest.mark.django_db
def test_database_rejects_user_account_without_person():
    with pytest.raises(IntegrityError):
        get_user_model().objects.create(username="orphan-account")


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.security
@pytest.mark.django_db
def test_registered_guardian_can_receive_guardian_account(client):
    administrator = UserFactory(is_superuser=True)
    guardian = GuardianFactory()
    client.force_login(administrator)

    response = client.post(
        reverse("identity-account-provision"),
        {
            "person": guardian.person_id,
            "username": "registered-guardian-account",
            "account_kind": "guardian",
        },
    )

    assert response.status_code == 201
    assert response.json()["person"] == guardian.person_id
