from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.services import create_teaching_assignment
from apps.audit.models import AuditEvent
from apps.identity.scopes import scope_matches
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.teachers import TeacherFactory

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


def test_write_scope_denies_mutations_when_cycle_transitions_to_closed():
    """
    RF-ALC-005 (Integration): Cross-domain validation that active teaching assignments
    and administrative grants automatically lose write capabilities once the cycle closes.
    """
    cycle = AcademicCycleFactory(status="active")
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=cycle.institution)
    teacher = TeacherFactory()
    teacher_user = UserFactory(person=teacher.person)

    write_permission = PermissionFactory(codename="grade_write")
    correct_permission = PermissionFactory(codename="grade_correct")
    read_permission = PermissionFactory(codename="student_view_basic")

    RoleAssignmentFactory(
        user=teacher_user,
        role=RoleFactory(permissions=[write_permission, correct_permission, read_permission]),
    )
    assignment = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
    )

    # 1. En ciclo activo, el docente tiene alcance de escritura
    assert (
        scope_matches(
            user=teacher_user,
            codename="grade_write",
            scope={"teaching_assignment": assignment},
        )
        is True
    )
    assert (
        scope_matches(
            user=teacher_user,
            codename="grade_write",
            scope={"section": section, "subject": subject},
        )
        is True
    )

    # 2. Transición del ciclo a cerrado
    cycle.status = cycle.CycleStatus.CLOSED
    cycle.save(update_fields=["status", "updated_at"])
    assignment.refresh_from_db()
    section.refresh_from_db()

    # 3. Tras el cierre, las operaciones de escritura quedan inmediatamente denegadas
    assert (
        scope_matches(
            user=teacher_user,
            codename="grade_write",
            scope={"teaching_assignment": assignment},
        )
        is False
    )
    assert (
        scope_matches(
            user=teacher_user,
            codename="grade_correct",
            scope={"teaching_assignment": assignment},
        )
        is False
    )

    # 4. Las operaciones de lectura administrativa sobre la estructura cerrada se preservan
    admin_user = UserFactory()
    admin_role = RoleFactory(permissions=[write_permission, read_permission])
    admin_assignment = RoleAssignmentFactory(user=admin_user, role=admin_role)
    ScopeGrantFactory(assignment=admin_assignment, section=section)

    assert (
        scope_matches(
            user=admin_user,
            codename="student_view_basic",
            scope={"section": section},
        )
        is True
    )
    assert (
        scope_matches(
            user=admin_user,
            codename="grade_write",
            scope={"section": section},
        )
        is False
    )
