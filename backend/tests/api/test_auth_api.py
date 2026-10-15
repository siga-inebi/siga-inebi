import json
import os
import subprocess
import sys
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


_COOKIE_SETTINGS = (
    "SESSION_COOKIE_HTTPONLY",
    "SESSION_COOKIE_SECURE",
    "SESSION_COOKIE_SAMESITE",
    "CSRF_COOKIE_SECURE",
    "CSRF_COOKIE_SAMESITE",
)


def _cookie_settings_of(module, environment):
    """Import a settings profile in a clean interpreter, as the server would."""
    env = {
        **os.environ,
        "DJANGO_SECRET_KEY": "cookie-profile-test-only",
        "DJANGO_ALLOWED_HOSTS": "localhost",
        "DJANGO_ENVIRONMENT": environment,
        "DATABASE_ENGINE": "postgresql",
    }
    script = (
        "import json\n"
        "from django.conf import global_settings as g\n"
        f"from config.settings import {module} as s\n"
        f"names = {list(_COOKIE_SETTINGS)!r}\n"
        "print(json.dumps({n: getattr(s, n, getattr(g, n)) for n in names}))\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed Python snippet with synthetic settings
        [sys.executable, "-c", script], capture_output=True, text=True, env=env, check=False
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("module", "environment"),
    [("base", "staging"), ("base", "production"), ("production", "production")],
)
def test_login_sets_session_cookie_with_httponly_secure_and_samesite(client, module, environment):
    """
    RNF-SEG-001: con el perfil base (fuera de desarrollo) y con el perfil de
    produccion -- no solo el de Cloud Run -- el login real emite la cookie de
    sesion con HttpOnly, Secure y SameSite=Lax/Strict, y la cookie CSRF con
    Secure y SameSite. Se leen los valores del perfil importado en limpio y se
    verifican sobre las cabeceras Set-Cookie de la respuesta.
    """
    profile = _cookie_settings_of(module, environment)
    user = UserFactory(password="demo-pass-123")

    with override_settings(**profile):
        csrf_response = client.get(reverse("auth-login"))
        login_response = client.post(
            reverse("auth-login"),
            {"username": user.username, "password": "demo-pass-123"},
        )

    assert login_response.status_code == 200
    session_cookie = login_response.cookies["sessionid"]
    assert session_cookie["httponly"] is True
    assert session_cookie["secure"] is True
    assert session_cookie["samesite"] in {"Lax", "Strict"}
    set_cookie = session_cookie.output()
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=" in set_cookie

    csrf_cookie = csrf_response.cookies["csrftoken"]
    assert csrf_cookie["secure"] is True
    assert csrf_cookie["samesite"] in {"Lax", "Strict"}
