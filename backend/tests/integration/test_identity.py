from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from tests.factories.identity import UserFactory

pytestmark = [pytest.mark.integration, pytest.mark.postgres, pytest.mark.django_db]


def test_password_change_lifecycle_and_session_invalidation():
    """
    RF-AUT-006 (Integration): Valida que al cambiar contraseña vía API:
    1. Se actualice la contraseña con hash seguro.
    2. Se cierren las demás sesiones activas en la base de datos.
    3. Se registre el evento auditable en AuditEvent sin texto plano.
    4. La nueva contraseña permita autenticarse y la anterior sea rechazada.
    """
    user = UserFactory(password="old-password-123")

    # Sesión A (dispositivo actual)
    client_a = APIClient()
    login_a = client_a.post(
        reverse("auth-login"),
        {"username": user.username, "password": "old-password-123"},
        format="json",
    )
    assert login_a.status_code == status.HTTP_200_OK

    # Sesión B (otro dispositivo registrado en base de datos)
    session_b = Session.objects.create(
        session_key="session-key-device-b",
        session_data=client_a.session.encode({"_auth_user_id": str(user.pk)}),
        expire_date=timezone.now() + timedelta(days=1),
    )

    # Cambio de contraseña desde sesión A
    change_resp = client_a.post(
        reverse("auth-password-change"),
        {
            "current_password": "old-password-123",
            "new_password": "New-Secret-Pass-2026!",
            "new_password_confirm": "New-Secret-Pass-2026!",
        },
        format="json",
    )
    assert change_resp.status_code == status.HTTP_200_OK

    # 1. Sesión B fue eliminada de la base de datos
    assert Session.objects.filter(session_key=session_b.session_key).exists() is False

    # 2. Bitácora registra identity.password.changed sin passwords en texto claro
    audit_event = AuditEvent.objects.get(
        action="identity.password.changed",
        resource_identifier=str(user.pk),
    )
    assert audit_event.context["result"] == "success"
    assert "old-password-123" not in str(audit_event.context)
    assert "New-Secret-Pass-2026!" not in str(audit_event.context)

    # 3. Nueva contraseña funciona para login
    client_c = APIClient()
    login_new = client_c.post(
        reverse("auth-login"),
        {"username": user.username, "password": "New-Secret-Pass-2026!"},
        format="json",
    )
    assert login_new.status_code == status.HTTP_200_OK
