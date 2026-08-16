import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories.identity import UserFactory

pytestmark = [pytest.mark.api, pytest.mark.postgres, pytest.mark.django_db]


def test_password_change_api_success_with_valid_credentials():
    """RF-AUT-006 (API): Usuario autenticado cambia su contraseña correctamente."""
    user = UserFactory(password="old-password-123")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        reverse("auth-password-change"),
        {
            "current_password": "old-password-123",
            "new_password": "New-Valid-Pass-2026!",
            "new_password_confirm": "New-Valid-Pass-2026!",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ok"
    user.refresh_from_db()
    assert user.check_password("New-Valid-Pass-2026!") is True


def test_password_change_api_rejects_incorrect_current_password():
    """RF-AUT-006 (API): Rechazo cuando la contraseña actual no coincide."""
    user = UserFactory(password="old-password-123")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        reverse("auth-password-change"),
        {
            "current_password": "wrong-current-password",
            "new_password": "New-Valid-Pass-2026!",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "incorrecta" in response.json()["error"]["detail"]["current_password"][0]


def test_password_change_api_requires_authentication():
    """RF-AUT-006 (API): Rechazo si el usuario no está autenticado."""
    client = APIClient()
    response = client.post(
        reverse("auth-password-change"),
        {
            "current_password": "any",
            "new_password": "any",
        },
        format="json",
    )
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
