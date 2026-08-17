import pytest
from django.urls import reverse
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories.identity import UserFactory
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.services import create_teaching_assignment
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.teachers import TeacherFactory

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
def test_api_rejection_for_write_operation_on_closed_cycle():
    """
    Validar que el API rechace mutaciones cuando el actor
    intenta operar sobre una asignación de un ciclo cerrado.
    """
    cycle = AcademicCycleFactory(status="active")
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=cycle.institution)
    teacher = TeacherFactory()
    teacher_user = UserFactory(person=teacher.person)

    write_permission = PermissionFactory(codename="grade_write")
    RoleAssignmentFactory(
        user=teacher_user,
        role=RoleFactory(permissions=[write_permission]),
    )
    assignment = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
    )

    client = APIClient()
    client.force_authenticate(user=teacher_user)

    # El ciclo se cierra
    cycle.status = cycle.CycleStatus.CLOSED
    cycle.save(update_fields=["status", "updated_at"])
    assignment.refresh_from_db()

    # Intento de realizar escritura sobre el ciclo cerrado a través de endpoints
    assert (
        teacher_user.has_scoped_permission(
            "grade_write",
            scope={"teaching_assignment": assignment},
        )
        is False
    )

    # Endpoint protegido por permisos responde denegado (403 Forbidden)
    response = client.post(
        reverse("teaching-assignment-reassign", args=[assignment.public_id]),
        {"teacher_id": str(TeacherFactory().public_id), "ends_on": "2026-06-30"},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
