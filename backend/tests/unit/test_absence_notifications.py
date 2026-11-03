"""
RF-JOR-007 — el padre recibe una notificacion cuando su hijo registra una
inasistencia (HU-14, RN-NOT-001). Servicio de dominio, sin capa API.
"""

from datetime import datetime, time

import pytest
from django.utils import timezone

from apps.attendance import services
from apps.attendance.models import (
    AbsenceNotification,
    AttendanceEvent,
    DayStatus,
    RecalculationReason,
)
from apps.audit.models import AuditEvent
from apps.enrolments.services import create_enrolment
from apps.students.services import create_student_guardian_relation
from tests.factories.academic import SectionFactory
from tests.factories.attendance import AttendanceEventFactory, JornadaParametersFactory
from tests.factories.students import GuardianFactory, StudentFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _at(event_date, hour, minute):
    return timezone.make_aware(datetime.combine(event_date, time(hour, minute)))


def _enrolled_student(parameters):
    section = SectionFactory(academic_cycle=parameters.academic_cycle, shift=parameters.shift)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=parameters.academic_cycle,
        grade=section.offering.grade,
        section=section,
    )
    return student


def test_notify_absence_addresses_only_the_primary_guardian():
    """
    RF-JOR-007: la notificacion de inasistencia se dirige a la asociacion
    principal vigente del estudiante (destinataria por defecto), no a los
    demas encargados vigentes.
    """
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    primary = GuardianFactory()
    secondary = GuardianFactory()
    primary_relation = create_student_guardian_relation(
        student=student, guardian=primary, relationship_label="Madre"
    )
    create_student_guardian_relation(
        student=student, guardian=secondary, relationship_label="Padre"
    )

    notification = services.notify_absence(
        student=student, shift=parameters.shift, absence_date=parameters.effective_from
    )

    assert notification.guardian == primary
    assert notification.relation == primary_relation
    assert notification.reason == AbsenceNotification.Reason.ABSENCE
    assert notification.superseded_at is None
    assert AbsenceNotification.objects.filter(student=student).count() == 1
    assert AuditEvent.objects.filter(
        action="attendance.absence_notification.created",
        resource_identifier=str(notification.public_id),
    ).exists()


def test_notify_absence_is_idempotent_per_student_date_and_reason():
    """RF-JOR-007: reprocesar la misma inasistencia no duplica la notificacion."""
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    create_student_guardian_relation(
        student=student, guardian=GuardianFactory(), relationship_label="Madre"
    )

    first = services.notify_absence(
        student=student, shift=parameters.shift, absence_date=parameters.effective_from
    )
    second = services.notify_absence(
        student=student, shift=parameters.shift, absence_date=parameters.effective_from
    )

    assert first == second
    assert AbsenceNotification.objects.filter(student=student).count() == 1
    assert AuditEvent.objects.filter(action="attendance.absence_notification.created").count() == 1


def test_notify_absence_without_a_current_primary_guardian_does_not_fail():
    """RF-JOR-007: sin encargado principal vigente no hay destinatario y no se falla."""
    parameters = JornadaParametersFactory()
    student = StudentFactory()

    result = services.notify_absence(
        student=student, shift=parameters.shift, absence_date=parameters.effective_from
    )

    assert result is None
    assert not AbsenceNotification.objects.exists()


def test_close_jornada_notifies_the_primary_guardian_of_an_absent_student_once():
    """
    RF-JOR-007: el cierre de jornada determina la inasistencia
    (``ausente_pendiente_justificar``) y notifica al encargado principal;
    repetir el cierre no duplica la notificacion. Un estudiante presente o
    sin encargado no genera notificacion ni hace fallar el cierre.
    """
    parameters = JornadaParametersFactory(closing_time=time(16, 0))
    absent = _enrolled_student(parameters)
    present = _enrolled_student(parameters)
    without_guardian = _enrolled_student(parameters)
    guardian = GuardianFactory()
    for student in (absent, present):
        create_student_guardian_relation(
            student=student, guardian=guardian, relationship_label="Madre"
        )
    AttendanceEventFactory(
        student=present,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(parameters.effective_from, 7, 0),
    )

    result = services.close_jornada(shift=parameters.shift, event_date=parameters.effective_from)
    services.close_jornada(shift=parameters.shift, event_date=parameters.effective_from)

    status = next(s for s in result.statuses if s.student == absent)
    assert status.status == DayStatus.ABSENT_PENDING_JUSTIFICATION
    notifications = AbsenceNotification.objects.all()
    assert [n.student for n in notifications] == [absent]
    assert notifications[0].guardian == guardian
    assert not AbsenceNotification.objects.filter(student=without_guardian).exists()


def test_later_entry_supersedes_the_absence_notification_without_deleting_it():
    """
    RF-JOR-007 + RF-JOR-006: si un ingreso registrado despues corrige la
    inasistencia, la notificacion se conserva marcada como superada.
    """
    parameters = JornadaParametersFactory(closing_time=time(16, 0))
    student = _enrolled_student(parameters)
    create_student_guardian_relation(
        student=student, guardian=GuardianFactory(), relationship_label="Madre"
    )
    services.close_jornada(shift=parameters.shift, event_date=parameters.effective_from)
    AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.MANUAL,
        captured_at=_at(parameters.effective_from, 7, 15),
    )

    services.recalculate_day(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        reason=RecalculationReason.LATE_EVENT,
        as_of=_at(parameters.effective_from, 17, 0),
    )

    notification = AbsenceNotification.objects.get(student=student)
    assert notification.superseded_at is not None
    assert notification.superseded_reason == RecalculationReason.LATE_EVENT
