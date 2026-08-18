from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.enrolments.services import change_section, create_enrolment
from apps.identity.services import assign_role, authenticate_account, disable_account
from tests.factories.academic import SectionFactory
from tests.factories.identity import PermissionFactory, RoleFactory, UserFactory
from tests.factories.students import StudentFactory


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_sensitive_write_produces_audit_event():
    actor = UserFactory(is_superuser=True)
    student = StudentFactory()
    section = SectionFactory()

    create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        actor=actor,
    )

    event = AuditEvent.objects.latest("created_at")
    assert event.actor_id == actor.id
    assert event.action == "enrolments.enrolment.created"


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_audit_event_actor_persists_after_user_deleted():
    actor = UserFactory(is_superuser=True)
    event = record_event(
        actor=actor,
        action="test.action",
        resource="Resource",
        resource_identifier="1",
        context={"password": "secret", "safe": "ok"},
    )

    actor.delete()
    event.refresh_from_db()

    assert event.actor is None
    assert event.actor_label
    assert "password" not in event.context
    assert event.context["safe"] == "ok"


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_audit_event_cannot_be_modified_or_deleted():
    event = record_event(
        actor=None,
        action="test.action",
        resource="Resource",
        resource_identifier="1",
    )

    with pytest.raises(RuntimeError):
        event.delete()

    with pytest.raises(RuntimeError):
        event.action = "changed"
        event.save()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_modifying_an_already_registered_academic_record_is_audited():
    """
    RF-BIT-001's own scenario ("GIVEN un docente que modifica una calificación
    ya registrada, WHEN confirma el cambio, THEN el sistema crea un asiento de
    bitácora"), substituted with a real equivalent: grade/score capture isn't
    modelled anywhere yet, but changing a student's section on an already
    registered enrolment is the same shape -- authorized staff modifies an
    existing academic record -- and it exists today.
    """
    actor = UserFactory(is_superuser=True)
    first_section = SectionFactory(name="A")
    second_section = SectionFactory(
        academic_cycle=first_section.academic_cycle,
        grade=first_section.grade,
        shift=first_section.shift,
        name="B",
    )
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=first_section.academic_cycle,
        grade=first_section.grade,
        section=first_section,
        actor=actor,
    )

    change_section(enrolment=enrolment, new_section=second_section, actor=actor)

    event = AuditEvent.objects.latest("created_at")
    assert event.actor_id == actor.id
    assert "section" in event.action or "enrolment" in event.action


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_successful_login_clearing_stale_lockout_is_audited():
    """
    RF-BIT-001 gap found by exhaustive review of every write path: a
    successful login that clears a previously recorded lockout state
    persisted the change without an audit entry.
    """
    user = UserFactory(password="correct-pass-123")
    user.failed_login_attempts = 3
    user.locked_until = timezone.now() - timedelta(seconds=1)  # expired, not locked
    user.save(update_fields=["failed_login_attempts", "locked_until"])

    authenticate_account(request=None, username=user.username, password="correct-pass-123")

    event = AuditEvent.objects.latest("created_at")
    assert event.action == "identity.login.lockout_cleared"
    assert event.actor_id == user.id
    assert event.context["cleared_failed_attempts"] == 3


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_disabling_an_account_with_a_declared_reason_is_audited():
    """
    RF-BIT-002's own scenario ("GIVEN un usuario que registra manualmente un
    movimiento indicando el motivo, WHEN se consulta el asiento
    correspondiente, THEN incluye usuario, acción, fecha y hora, registro
    afectado, dispositivo y motivo"), substituted with a real equivalent:
    attendance's manual-entry path is an explicitly provisional skeleton
    ("A separate attendance-capture effort owns the real scanning/ingestion
    workflow and may replace this mapping" -- apps/attendance/api/views.py).
    Disabling an account with a declared reason is the same shape -- a
    sensitive operation that requires a user-declared motivo -- on stable
    code.
    """
    actor = UserFactory(is_superuser=True)
    target = UserFactory()

    disable_account(actor=actor, user=target, reason="Solicitud del titular")

    event = AuditEvent.objects.latest("created_at")
    assert event.actor_id == actor.id
    assert event.action == "identity.account.disabled"
    assert event.resource_identifier == str(target.pk)
    assert event.context["reason"] == "Solicitud del titular"
    assert "before" in event.context and "after" in event.context


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_denied_operation_can_be_audited():
    actor = UserFactory()
    target = UserFactory()
    role = RoleFactory(permissions=[PermissionFactory(codename="role_assign")])

    with pytest.raises(PermissionDenied):
        assign_role(actor=actor, user=target, role=role)

    denied_event = record_event(
        actor=actor,
        action="identity.role_assignment.denied",
        resource="RoleAssignment",
        context={"reason": "missing_permission"},
    )
    assert denied_event.action.endswith("denied")
