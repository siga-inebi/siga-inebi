from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from tests.factories.identity import UserFactory

pytestmark = [pytest.mark.integration, pytest.mark.postgres, pytest.mark.django_db]


def test_lockout_lifecycle_consecutive_failures_lock_and_auto_recover():
    """
    RF-AUT-002 (Integration): Verifica el ciclo completo de bloqueo tras 5 intentos fallidos,
    rechazo de contraseña válida durante el bloqueo, registro en bitácora y recuperación
    automática al expirar el tiempo de bloqueo.
    """
    user = UserFactory(password="secure-pass-2026")
    client = APIClient()

    # 1. Ejecución de 5 intentos fallidos consecutivos vía API
    for _attempt in range(1, 6):
        response = client.post(
            reverse("auth-login"),
            {"username": user.username, "password": "wrong-password"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    user.refresh_from_db()
    assert user.failed_login_attempts == 5
    assert user.locked_until is not None
    assert user.is_locked() is True

    # 2. Verificar que se registraron eventos en bitácora para cada intento fallido y bloqueo
    denied_events = AuditEvent.objects.filter(
        action="identity.login.denied",
        resource_identifier=str(user.pk),
    )
    assert denied_events.count() == 5
    last_event = denied_events.latest("created_at")
    assert last_event.context["reason"] == "temporarily_locked"
    assert "locked_until" in last_event.context

    # 3. Escenario 1: Intento con contraseña correcta mientras la cuenta está bloqueada
    blocked_response = client.post(
        reverse("auth-login"),
        {"username": user.username, "password": "secure-pass-2026"},
        format="json",
    )
    assert blocked_response.status_code == status.HTTP_400_BAD_REQUEST
    assert "bloqueada" in blocked_response.json()["error"]["detail"]["non_field_errors"][0]

    # 4. Escenario 2: Levantamiento automático tras transcurrir el lapso configurado
    user.locked_until = timezone.now() - timedelta(seconds=1)
    user.save(update_fields=["locked_until"])

    success_response = client.post(
        reverse("auth-login"),
        {"username": user.username, "password": "secure-pass-2026"},
        format="json",
    )
    assert success_response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
    assert user.is_locked() is False
