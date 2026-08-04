from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from tests.factories.identity import UserFactory


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.django_db
def test_me_without_session_returns_anonymous_payload(client):
    response = client.get(reverse("auth-me"))

    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "user": None}


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.security
@pytest.mark.django_db
def test_login_get_sets_csrf_cookie(client):
    response = client.get(reverse("auth-login"))

    assert response.status_code == 204
    assert "csrftoken" in response.cookies


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.security
@pytest.mark.django_db
def test_login_and_logout_roundtrip(client):
    user = UserFactory(password="demo-pass-123")

    login_response = client.post(
        reverse("auth-login"),
        {"username": user.username, "password": "demo-pass-123"},
    )
    assert login_response.status_code == 200
    assert "password" not in login_response.json()
    assert "_auth_user_id" in client.session
    assert login_response.json()["username"] == user.username

    me_response = client.get(reverse("auth-me"))
    assert me_response.status_code == 200
    assert me_response.json()["authenticated"] is True
    assert me_response.json()["user"]["username"] == user.username
    assert "password" not in me_response.json()["user"]

    logout_response = client.post(reverse("auth-logout"))
    assert logout_response.status_code == 204
    assert "_auth_user_id" not in client.session

    me_after_logout = client.get(reverse("auth-me"))
    assert me_after_logout.status_code == 200
    assert me_after_logout.json()["authenticated"] is False


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_inactive_user_cannot_login(client):
    user_model = get_user_model()
    user = UserFactory(password="demo-pass-123")
    user.is_active = False
    user.status = user_model.AccountStatus.DISABLED
    user.save(update_fields=["is_active", "status"])

    response = client.post(
        reverse("auth-login"),
        {"username": user.username, "password": "demo-pass-123"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["detail"]["non_field_errors"] == ["Credenciales invalidas."]
    assert "_auth_user_id" not in client.session


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
@override_settings(LOGIN_MAX_FAILED_ATTEMPTS=5, LOGIN_LOCKOUT_MINUTES=10)
def test_fifth_failed_login_temporarily_locks_account_and_audits_attempts(client):
    user = UserFactory(password="correct-pass-123")

    for attempt in range(1, 6):
        response = client.post(
            reverse("auth-login"),
            {"username": user.username, "password": "wrong-pass-123"},
        )
        user.refresh_from_db()
        assert user.failed_login_attempts == attempt

    assert response.status_code == 400
    assert response.json()["error"]["detail"]["non_field_errors"] == [
        "Cuenta temporalmente bloqueada."
    ]
    assert user.locked_until is not None
    assert timedelta(minutes=9, seconds=55) <= user.locked_until - timezone.now()
    assert (
        AuditEvent.objects.filter(
            action="identity.login.denied",
            resource_identifier=str(user.pk),
        ).count()
        == 5
    )


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_locked_account_cannot_login_with_correct_password(client):
    user = UserFactory(password="correct-pass-123")
    user.failed_login_attempts = 5
    user.locked_until = timezone.now() + timedelta(minutes=10)
    user.save(update_fields=["failed_login_attempts", "locked_until"])

    response = client.post(
        reverse("auth-login"),
        {"username": user.username, "password": "correct-pass-123"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["detail"]["non_field_errors"] == [
        "Cuenta temporalmente bloqueada."
    ]
    assert "_auth_user_id" not in client.session


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_successful_login_resets_previous_failed_attempts(client):
    user = UserFactory(password="correct-pass-123", failed_login_attempts=3)

    response = client.post(
        reverse("auth-login"),
        {"username": user.username, "password": "correct-pass-123"},
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_expired_lock_allows_login_and_resets_counter(client):
    user = UserFactory(password="correct-pass-123")
    user.failed_login_attempts = 5
    user.locked_until = timezone.now() - timedelta(seconds=1)
    user.save(update_fields=["failed_login_attempts", "locked_until"])

    response = client.post(
        reverse("auth-login"),
        {"username": user.username, "password": "correct-pass-123"},
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
