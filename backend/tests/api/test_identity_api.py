from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories.identity import UserFactory

pytestmark = [pytest.mark.api, pytest.mark.postgres, pytest.mark.django_db]


def test_api_rejection_for_temporarily_locked_account():
    """
    RF-AUT-002 (API): Validar que el endpoint /api/v1/auth/login/ rechace
    la autenticación con HTTP 400 cuando la cuenta está temporalmente bloqueada.
    """
    user = UserFactory(password="correct-pass-123")
    user.failed_login_attempts = 5
    user.locked_until = timezone.now() + timedelta(minutes=10)
    user.save(update_fields=["failed_login_attempts", "locked_until"])

    client = APIClient()

    # Escenario 1: Intento con contraseña correcta mientras está bloqueado
    response = client.post(
        reverse("auth-login"),
        {"username": user.username, "password": "correct-pass-123"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["detail"]["non_field_errors"] == [
        "Cuenta temporalmente bloqueada."
    ]


def test_api_allows_login_after_lockout_period_expires():
    """
    RF-AUT-002 (API): Validar que el endpoint permita el inicio de sesión
    una vez transcurrido el tiempo configurado de bloqueo.
    """
    user = UserFactory(password="correct-pass-123")
    user.failed_login_attempts = 5
    user.locked_until = timezone.now() - timedelta(seconds=1)
    user.save(update_fields=["failed_login_attempts", "locked_until"])

    client = APIClient()

    # Escenario 2: Intento con contraseña correcta tras expirar el bloqueo
    response = client.post(
        reverse("auth-login"),
        {"username": user.username, "password": "correct-pass-123"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
