import pytest

from apps.academics.models import TeachingAssignment
from apps.academics.services import publish_class_schedule
from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.common.exceptions import AuthorizationError
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment
from apps.enrolments.services import create_enrolment
from apps.identity.services import (
    assign_role,
    create_role,
    disable_account,
    filter_queryset_by_scope,
    list_atomic_permissions,
    my_weekly_schedule,
    revoke_role_assignment,
    update_role,
)
from apps.students.models import Student
from tests.factories.academic import (
    AcademicCycleFactory,
    ClassSessionFactory,
    SectionFactory,
    SubjectFactory,
)
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.students import GuardianFactory, StudentFactory, StudentGuardianRelationFactory
from tests.factories.teachers import TeacherFactory


@pytest.mark.django_db
def test_permission_catalog_requires_administrative_permission():
    actor = UserFactory()

    with pytest.raises(AuthorizationError):
        list_atomic_permissions(actor=actor)

    event = AuditEvent.objects.get(action="identity.permission_catalog.read_denied")
    assert event.actor == actor
    assert event.context["reason"] == "missing_permission"


@pytest.mark.django_db
def test_permission_catalog_returns_only_registered_atomic_permissions():
    actor = UserFactory()
    role_assign = PermissionFactory(codename="role_assign")
    RoleAssignmentFactory(user=actor, role=RoleFactory(permissions=[role_assign]))
    PermissionFactory(codename="unregistered_permission")

    permissions = list(list_atomic_permissions(actor=actor))

    codenames = {permission.codename for permission in permissions}
    assert "role_assign" in codenames
    assert "attendance_record_entry" in codenames
    assert "attendance_record_exit" in codenames
    assert "attendance_declared_close" in codenames
    assert "unregistered_permission" not in codenames
    event = AuditEvent.objects.get(action="identity.permission_catalog.read")
    assert event.context["permission_count"] == len(permissions)


@pytest.mark.django_db
def test_role_composition_change_applies_to_assigned_accounts_and_is_audited():
    actor = UserFactory(is_superuser=True)
    target = UserFactory()
    role = create_role(
        actor=actor,
        name="Attendance Operator",
        slug="attendance-operator-custom",
        permission_codenames=["attendance_record_entry"],
    )
    assignment = RoleAssignmentFactory(user=target, role=role)

    assert (
        target.has_scoped_permission("attendance_record_exit", scope={"module_key": "identity"})
        is False
    )

    update_role(
        actor=actor,
        role=role,
        permission_codenames=["attendance_record_entry", "attendance_record_exit"],
    )

    assert (
        target.has_scoped_permission("attendance_record_exit", scope={"module_key": "identity"})
        is True
    )
    event = AuditEvent.objects.get(action="identity.role.updated")
    assert event.actor == actor
    assert event.context["before"]["permissions"] == ["attendance_record_entry"]
    assert event.context["after"]["permissions"] == [
        "attendance_record_entry",
        "attendance_record_exit",
    ]
    assert assignment.user_id == target.pk


@pytest.mark.django_db
def test_revoked_role_is_denied_on_next_permission_evaluation():
    actor = UserFactory(is_superuser=True)
    target = UserFactory()
    permission = PermissionFactory(codename="audit_read")
    assignment = RoleAssignmentFactory(
        user=target,
        role=RoleFactory(permissions=[permission]),
    )

    assert target.has_scoped_permission("audit_read", scope={"module_key": "identity"}) is True

    revoke_role_assignment(actor=actor, assignment=assignment)

    assert target.has_scoped_permission("audit_read", scope={"module_key": "identity"}) is False
    assert AuditEvent.objects.filter(
        action="identity.role_assignment.revoked",
        actor=actor,
    ).exists()


@pytest.mark.django_db
def test_role_assignment_requires_explicit_scope():
    actor = UserFactory(is_superuser=True)

    with pytest.raises(DomainError, match="alcance explicito"):
        assign_role(actor=actor, user=UserFactory(), role=RoleFactory(), scope=None)


@pytest.mark.django_db
def test_last_account_administrator_role_cannot_be_revoked():
    actor = UserFactory(is_superuser=True)
    account_create = PermissionFactory(codename="account_create")
    protected = RoleAssignmentFactory(
        role=RoleFactory(permissions=[account_create]),
    )

    with pytest.raises(DomainError, match="ultimo administrador de cuentas"):
        revoke_role_assignment(actor=actor, assignment=protected)

    RoleAssignmentFactory(role=RoleFactory(permissions=[account_create]))
    revoked = revoke_role_assignment(actor=actor, assignment=protected)

    assert revoked.ends_at is not None


@pytest.mark.django_db
def test_last_administrator_role_cannot_lose_account_create_permission():
    actor = UserFactory(is_superuser=True)
    account_create = PermissionFactory(codename="account_create")
    protected_role = RoleFactory(permissions=[account_create])
    RoleAssignmentFactory(role=protected_role)

    with pytest.raises(DomainError, match="ultimo administrador de cuentas"):
        update_role(actor=actor, role=protected_role, permission_codenames=[])

    RoleAssignmentFactory(role=RoleFactory(permissions=[account_create]))
    updated = update_role(actor=actor, role=protected_role, permission_codenames=[])

    assert updated.permissions.exists() is False


@pytest.mark.django_db
def test_last_account_administrator_cannot_be_disabled():
    actor = UserFactory(is_superuser=True)
    account_create = PermissionFactory(codename="account_create")
    protected = RoleAssignmentFactory(role=RoleFactory(permissions=[account_create])).user

    with pytest.raises(DomainError, match="ultimo administrador de cuentas"):
        disable_account(actor=actor, user=protected)

    RoleAssignmentFactory(role=RoleFactory(permissions=[account_create]))
    result = disable_account(actor=actor, user=protected)

    assert result["disabled"] is True
    assert result["account"].is_active is False


@pytest.mark.django_db
def test_queryset_filter_only_returns_records_inside_effective_scope():
    permission = PermissionFactory(codename="student_view_basic")
    assignment = RoleAssignmentFactory(
        role=RoleFactory(permissions=[permission]),
        identity_scope=False,
    )
    allowed_section = SectionFactory()
    denied_section = SectionFactory()
    ScopeGrantFactory(assignment=assignment, section=allowed_section)
    allowed_student = StudentFactory()
    denied_student = StudentFactory()
    Enrolment.objects.create(
        student=allowed_student,
        academic_cycle=allowed_section.academic_cycle,
        grade=allowed_section.grade,
        section=allowed_section,
    )
    Enrolment.objects.create(
        student=denied_student,
        academic_cycle=denied_section.academic_cycle,
        grade=denied_section.grade,
        section=denied_section,
    )

    scoped_students = filter_queryset_by_scope(
        actor=assignment.user,
        codename="student_view_basic",
        queryset=Student.objects.all(),
        dimension="section",
        lookup="enrolments__section_id",
    )

    assert list(scoped_students) == [allowed_student]


# ---------------------------------------------------------------------------
# RF-CTA-007 — Prohibición de autoescalamiento
# RF-CTA-006 — Desactivación con verificación de dependencias
# RF-CTA-004 — Política de contraseñas
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rf_cta_007_self_role_assignment_is_rejected_and_audited():
    """Escenario 1: Intento de asignarse un rol adicional a sí mismo."""
    actor = UserFactory()
    role_admin = RoleFactory(permissions=[PermissionFactory(codename="role_assign")])
    RoleAssignmentFactory(user=actor, role=role_admin)
    extra_role = RoleFactory()

    with pytest.raises(AuthorizationError, match="Nadie puede asignarse roles a si mismo."):
        assign_role(
            actor=actor,
            user=actor,
            role=extra_role,
            scope={"module_key": "identity"},
        )

    event = AuditEvent.objects.filter(
        action="identity.role_assignment.create_denied",
        resource_identifier=str(actor.pk),
    ).latest("created_at")
    assert event.actor == actor
    assert event.context["reason"] == "self_escalation"


@pytest.mark.django_db
def test_rf_cta_007_self_role_revocation_is_rejected_and_audited():
    """Intento de revocar un rol propio -> rechazado y auditado."""
    actor = UserFactory()
    role_admin = RoleFactory(permissions=[PermissionFactory(codename="role_assign")])
    assignment = RoleAssignmentFactory(user=actor, role=role_admin)

    with pytest.raises(AuthorizationError, match="Nadie puede revocar sus propios roles."):
        revoke_role_assignment(actor=actor, assignment=assignment)

    event = AuditEvent.objects.filter(
        action="identity.role_assignment.revoke_denied",
        resource_identifier=str(assignment.public_id),
    ).latest("created_at")
    assert event.actor == actor
    assert event.context["reason"] == "self_escalation"


@pytest.mark.django_db
def test_rf_cta_007_self_account_disable_is_rejected_and_audited():
    """Intento de desactivar la propia cuenta -> rechazado y auditado."""
    actor = UserFactory()
    RoleAssignmentFactory(
        user=actor,
        role=RoleFactory(permissions=[PermissionFactory(codename="account_disable")]),
    )

    with pytest.raises(AuthorizationError, match="Nadie puede deshabilitar su propia cuenta."):
        disable_account(actor=actor, user=actor)

    event = AuditEvent.objects.filter(
        action="identity.account.disable_denied",
        resource_identifier=str(actor.pk),
    ).latest("created_at")
    assert event.actor == actor
    assert event.context["reason"] == "self_deactivation"


@pytest.mark.django_db
def test_rf_cta_006_disable_warns_about_active_teaching_assignments():
    """Escenario 1: docente con secciones vigentes → advierte antes de desactivar."""
    from apps.academics.models import AcademicCycle, TeachingAssignment

    actor = UserFactory(is_superuser=True)
    person = PersonFactory()
    target = UserFactory(person=person)
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=cycle.institution)
    TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=person,
    )

    result = disable_account(actor=actor, user=target, force=False)

    assert result["disabled"] is False
    assert len(result["warnings"]["teaching_assignments"]) == 1
    target.refresh_from_db()
    assert target.is_active is True  # No se desactivó


@pytest.mark.django_db
def test_rf_cta_006_disabled_account_historical_events_survive():
    """Escenario 2: eventos previos siguen atribuidos a la cuenta desactivada."""
    actor = UserFactory(is_superuser=True)
    target = UserFactory()

    record_event(
        actor=target,
        action="grades.published",
        resource="Grade",
        resource_identifier="test-grade",
        context={"detail": "nota publicada"},
    )

    disable_account(actor=actor, user=target, force=True)

    target.refresh_from_db()
    assert target.is_active is False

    event = AuditEvent.objects.get(action="grades.published")
    assert event.actor_id == target.pk


@pytest.mark.django_db
def test_rf_cta_004_common_password_is_rejected():
    """Escenario 1: contraseña presente en la lista de comunes → rechazada."""
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    user = UserFactory()
    with pytest.raises(ValidationError) as exc_info:
        validate_password("password", user=user)
    assert any("común" in msg or "common" in msg for msg in exc_info.value.messages)


@pytest.mark.django_db
def test_rf_cta_004_long_password_without_symbols_is_accepted():
    """Escenario 2: contraseña larga sin símbolos, no común → aceptada."""
    from django.contrib.auth.password_validation import validate_password

    user = UserFactory()
    # Solo minúsculas, sin mayúsculas, números ni símbolos; supera longitud mínima.
    validate_password("alargadaycorrecta", user=user)


@pytest.mark.django_db
def test_rf_aut_006_change_password_requires_correct_current_password():
    """RF-AUT-006: Rechaza cambio si la contraseña actual no coincide."""
    from apps.audit.models import AuditEvent
    from apps.identity.services import change_password

    user = UserFactory(password="old-secure-pass-123")

    with pytest.raises(DomainError, match="incorrecta"):
        change_password(
            user=user,
            current_password="wrong-password-999",
            new_password="New-Secure-Pass-2026!",
        )

    assert user.check_password("old-secure-pass-123") is True
    event = AuditEvent.objects.get(action="identity.password.change_denied")
    assert event.resource_identifier == str(user.pk)
    assert event.context["reason"] == "invalid_current_password"


@pytest.mark.django_db
def test_rf_aut_006_change_password_updates_password_and_invalidates_other_sessions(client):
    """RF-AUT-006: Cambia contraseña exitosamente y cierra las demás sesiones activas."""
    from datetime import timedelta

    from django.contrib.sessions.middleware import SessionMiddleware
    from django.contrib.sessions.models import Session
    from django.test import RequestFactory
    from django.utils import timezone

    from apps.audit.models import AuditEvent
    from apps.identity.services import change_password

    user = UserFactory(password="old-secure-pass-123")

    # Crear sesiones previas en base de datos para el mismo usuario
    session_other_1 = Session.objects.create(
        session_key="session-device-1",
        session_data=client.session.encode({"_auth_user_id": str(user.pk)}),
        expire_date=timezone.now() + timedelta(days=1),
    )
    session_other_2 = Session.objects.create(
        session_key="session-device-2",
        session_data=client.session.encode({"_auth_user_id": str(user.pk)}),
        expire_date=timezone.now() + timedelta(days=1),
    )

    rf = RequestFactory()
    request = rf.post("/api/v1/auth/password/change/")
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    request.session["_auth_user_id"] = str(user.pk)
    request.session.save()
    request.user = user

    updated_user = change_password(
        user=user,
        current_password="old-secure-pass-123",
        new_password="New-Secure-Pass-2026!",
        request=request,
    )

    assert updated_user.check_password("New-Secure-Pass-2026!") is True
    assert updated_user.check_password("old-secure-pass-123") is False

    # Las demás sesiones fueron eliminadas/cerradas
    assert Session.objects.filter(session_key=session_other_1.session_key).exists() is False
    assert Session.objects.filter(session_key=session_other_2.session_key).exists() is False

    # Registro en bitácora sin texto plano
    event = AuditEvent.objects.get(action="identity.password.changed")
    assert event.resource_identifier == str(user.pk)
    assert event.context["result"] == "success"
    assert "New-Secure-Pass-2026!" not in str(event.context)


@pytest.mark.django_db
def test_rf_aut_002_authenticate_account_locks_after_max_failed_attempts():
    """RF-AUT-002: Bloqueo tras superar el número configurado de intentos fallidos."""
    from django.utils import timezone

    from apps.identity.services import (
        AccountTemporarilyLockedError,
        InvalidCredentialsError,
        authenticate_account,
    )

    user = UserFactory(password="correct-pass-123")

    for _ in range(4):
        with pytest.raises(InvalidCredentialsError):
            authenticate_account(request=None, username=user.username, password="wrong-password")

    user.refresh_from_db()
    assert user.failed_login_attempts == 4
    assert user.locked_until is None

    # Quinto intento fallido activa el bloqueo temporal
    with pytest.raises(AccountTemporarilyLockedError):
        authenticate_account(request=None, username=user.username, password="wrong-password")

    user.refresh_from_db()
    assert user.failed_login_attempts == 5
    assert user.locked_until is not None
    assert user.locked_until > timezone.now()


@pytest.mark.django_db
def test_rf_aut_002_locked_account_rejects_correct_password_and_lifts_automatically():
    """RF-AUT-002: Cuenta bloqueada rechaza contraseña correcta y se desbloquea al expirar."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.identity.services import AccountTemporarilyLockedError, authenticate_account

    user = UserFactory(password="correct-pass-123")
    user.failed_login_attempts = 5
    user.locked_until = timezone.now() + timedelta(minutes=10)
    user.save(update_fields=["failed_login_attempts", "locked_until"])

    # Escenario 1: Intento con contraseña correcta mientras está bloqueado
    with pytest.raises(AccountTemporarilyLockedError):
        authenticate_account(request=None, username=user.username, password="correct-pass-123")

    # Escenario 2: Levantamiento automático tras transcurrir el lapso
    user.locked_until = timezone.now() - timedelta(seconds=1)
    user.save(update_fields=["locked_until"])

    authenticated_user = authenticate_account(
        request=None, username=user.username, password="correct-pass-123"
    )
    assert authenticated_user == user
    user.refresh_from_db()
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


@pytest.mark.django_db
def test_scope_matches_denies_write_permissions_on_closed_cycle():
    from apps.identity.scopes import scope_matches
    from tests.factories.academic import AcademicCycleFactory

    closed_cycle = AcademicCycleFactory(status="closed")
    section = SectionFactory(academic_cycle=closed_cycle)
    user = UserFactory()
    write_permission = PermissionFactory(codename="grade_write")
    assignment = RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[write_permission]),
    )
    ScopeGrantFactory(assignment=assignment, section=section)

    assert (
        scope_matches(
            user=user,
            codename="grade_write",
            scope={"section": section},
        )
        is False
    )


# --------------------------------------------------------------------------- #
# my weekly schedule (RF-HOR-010)
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_my_weekly_schedule_returns_the_teachers_own_sessions():
    """Escenario 1 (#203): docente ve su propia sesion, ciclo publicado."""
    session = ClassSessionFactory()
    publish_class_schedule(academic_cycle=session.academic_cycle)
    teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=session.academic_cycle,
        section=session.section,
        subject=session.subject,
        teacher=teacher.person,
        starts_on=session.academic_cycle.starts_on,
    )
    user = UserFactory(person=teacher.person)

    assert list(my_weekly_schedule(actor=user)) == [session]


@pytest.mark.django_db
def test_my_weekly_schedule_excludes_sessions_of_an_unpublished_cycle():
    """Un ciclo sin publicar no aparece, aunque el docente tenga asignacion vigente."""
    session = ClassSessionFactory()
    teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=session.academic_cycle,
        section=session.section,
        subject=session.subject,
        teacher=teacher.person,
        starts_on=session.academic_cycle.starts_on,
    )
    user = UserFactory(person=teacher.person)

    assert list(my_weekly_schedule(actor=user)) == []


@pytest.mark.django_db
def test_my_weekly_schedule_excludes_a_session_of_an_unrelated_subject():
    """El docente que da Matematica en la seccion A no ve Comunicacion en esa misma seccion."""
    session = ClassSessionFactory()
    publish_class_schedule(academic_cycle=session.academic_cycle)
    other_subject = SubjectFactory(institution=session.section.offering.institution)
    other_subject_session = ClassSessionFactory(section=session.section, subject=other_subject)
    teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=session.academic_cycle,
        section=session.section,
        subject=session.subject,
        teacher=teacher.person,
        starts_on=session.academic_cycle.starts_on,
    )
    user = UserFactory(person=teacher.person)

    schedule = list(my_weekly_schedule(actor=user))

    assert session in schedule
    assert other_subject_session not in schedule


@pytest.mark.django_db
def test_my_weekly_schedule_returns_a_guardians_ward_sessions():
    """Escenario 1 alterno (#203): encargado ve la sesion de su pupilo, ciclo publicado."""
    session = ClassSessionFactory()
    publish_class_schedule(academic_cycle=session.academic_cycle)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=session.academic_cycle,
        grade=session.section.grade,
        section=session.section,
    )
    guardian = GuardianFactory()
    StudentGuardianRelationFactory(student=student, guardian=guardian)
    user = UserFactory(person=guardian.person)

    assert list(my_weekly_schedule(actor=user)) == [session]


@pytest.mark.django_db
def test_my_weekly_schedule_rejects_an_account_without_teacher_or_guardian_scope():
    """Escenario 2 (#203): rechazo -- la cuenta no es docente ni encargado activo."""
    user = UserFactory()

    with pytest.raises(AuthorizationError, match="no esta vinculada"):
        my_weekly_schedule(actor=user)

    event = AuditEvent.objects.get(action="identity.my_schedule.read_denied")
    assert event.actor == user
    assert event.context["reason"] == "no_teacher_or_guardian_scope"
