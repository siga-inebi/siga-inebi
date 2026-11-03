"""
RF-BIT-001's security section: writes must keep respecting the domain's own
role/scope access control, and get audited either way -- allowed or denied.
"""

import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.audit.services import get_result_trace, record_event
from apps.common.exceptions import AuthorizationError
from apps.enrolments.services import create_enrolment
from apps.identity.models import Role
from apps.identity.scopes import authorized_student_queryset
from apps.identity.services import create_role
from tests.factories.academic import SectionFactory, SubjectFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.students import GuardianFactory, StudentFactory

pytestmark = [pytest.mark.permissions, pytest.mark.django_db]


def test_authorized_write_is_audited():
    permission = PermissionFactory(codename="role_assign")
    assignment = RoleAssignmentFactory(role=RoleFactory(permissions=[permission]))

    role = create_role(actor=assignment.user, name="Coordinador", slug="coordinador")

    assert Role.objects.filter(pk=role.pk).exists()
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "identity.role.created"
    assert event.actor_id == assignment.user.id
    assert event.context["result"] == "success"


def test_denied_write_is_still_audited():
    assignment = RoleAssignmentFactory(role=RoleFactory(permissions=[]))

    with pytest.raises(AuthorizationError):
        create_role(actor=assignment.user, name="Coordinador", slug="coordinador")

    event = AuditEvent.objects.latest("created_at")
    assert event.action == "identity.role.create_denied"
    assert event.context["result"] == "denied"
    assert not Role.objects.filter(slug="coordinador").exists()


def test_audit_events_cannot_be_listed_or_exported_without_the_audit_permission(auth_client):
    """
    RF-BIT-006: "La consulta de la bitacora DEBE estar restringida a los
    usuarios con permiso de auditoria." An authenticated user with no
    permissions at all must be rejected on both operations.
    """
    list_response = auth_client.get(reverse("audit-event-list"))
    export_response = auth_client.get(reverse("audit-event-export"))

    assert list_response.status_code == 403
    assert export_response.status_code == 403


def test_audit_event_cannot_be_deleted_even_by_the_highest_privilege_actor():
    """
    RF-BIT-005, Escenario 1: "GIVEN un usuario con el rol de mayor privilegio,
    WHEN intenta eliminar un asiento de bitacora, THEN el sistema no ofrece
    esa operacion y la rechaza si se invoca directamente."

    ``has_atomic_permission`` has no superuser bypass anywhere else in this
    system, so the highest-privilege actor available is a Django
    ``is_superuser=True`` account -- and even it is rejected, both through
    the instance and the queryset delete path.
    """
    actor = UserFactory(is_superuser=True)
    event = record_event(actor=actor, action="test.action", resource="Resource")

    with pytest.raises(RuntimeError):
        event.delete()

    with pytest.raises(RuntimeError):
        AuditEvent.objects.filter(pk=event.pk).delete()

    assert AuditEvent.objects.filter(pk=event.pk).exists()


def test_guardian_without_a_student_association_is_denied_and_audited():
    """
    RF-BIT-004, Escenario 1: "GIVEN un encargado sin asociacion con un
    estudiante, WHEN intenta acceder a la informacion de ese estudiante,
    THEN el sistema deniega la operacion y crea un asiento del intento."

    ``authorized_student_queryset`` is the single choke point every
    student-scoped view (directly, or via ``can_access_student``) goes
    through, so auditing there covers this scenario without duplicating the
    audit call at every view.
    """
    permission = PermissionFactory(codename="student_view_basic")
    guardian = GuardianFactory()
    user = UserFactory(person=guardian.person)
    RoleAssignmentFactory(
        user=user, role=RoleFactory(permissions=[permission]), identity_scope=False
    )
    StudentFactory()  # exists, but this guardian has no relation to it

    with pytest.raises(AuthorizationError):
        authorized_student_queryset(user=user, codename="student_view_basic")

    event = AuditEvent.objects.latest("created_at")
    assert event.action == "identity.authorization.denied"
    assert event.actor_id == user.id
    assert event.context["result"] == "denied"
    assert event.context["reason"] == "missing_scope"


def test_actor_without_the_permission_is_denied_and_audited():
    user = UserFactory()

    with pytest.raises(AuthorizationError):
        authorized_student_queryset(user=user, codename="student_view_basic")

    event = AuditEvent.objects.latest("created_at")
    assert event.action == "identity.authorization.denied"
    assert event.actor_id == user.id
    assert event.context["reason"] == "missing_permission"


def test_result_trace_endpoint_is_denied_without_audit_read_permission(auth_client):
    """
    RF-RES-009 security note: "dominio sensible -- respetar el control de
    acceso por rol y alcance". No permission at all -> denied, same as every
    other audit_read-gated endpoint (audit-event-list, audit-event-export).
    """
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    subject = SubjectFactory(institution=section.academic_cycle.institution)

    response = auth_client.get(
        reverse(
            "result-trace",
            kwargs={"enrolment_id": enrolment.public_id, "subject_id": subject.public_id},
        )
    )

    assert response.status_code == 403


def test_result_trace_view_is_recorded_as_a_sensitive_read_naming_the_student():
    """RF-BIT-003: viewing one identified student's result trace is audited
    as a sensitive read, regardless of what the trace finds."""
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    subject = SubjectFactory(institution=section.academic_cycle.institution)
    viewer = UserFactory()

    get_result_trace(enrolment=enrolment, subject=subject, actor=viewer)

    event = AuditEvent.objects.get(action="audit.result_trace.viewed")
    assert event.actor_id == viewer.id
    assert event.context["student_id"] == enrolment.student.pk
    assert event.context["result"] == "success"
