"""
RF-JOR-007 — alertas de asistencia, con matricula real y cruzando dominios
(attendance + reporting) contra Postgres.
"""

from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.attendance import services as attendance_services
from apps.attendance.models import AttendanceAlert, AttendanceEvent
from apps.enrolments.services import create_enrolment
from apps.reporting import services as reporting_services
from apps.reporting.models import Alert
from tests.factories.academic import AcademicCycleFactory, SectionFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.integration, pytest.mark.postgres, pytest.mark.django_db]


def _enrolled_student(cycle):
    section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    return student, section, section.offering.shift


def test_absence_alert_end_to_end_with_real_enrolment_and_section_coordinator_targeting():
    """
    Escenario 1 (RF-JOR-007): GIVEN un estudiante sin ingreso registrado al
    vencer la hora limite de su jornada, WHEN el sistema evalua las alertas
    del dia, THEN genera una alerta de ausencia dirigida al coordinador de
    aula correspondiente.
    """
    event_date = timezone.localdate()
    cycle = AcademicCycleFactory(starts_on=event_date - timedelta(days=30))
    student, section, shift = _enrolled_student(cycle)
    attendance_services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )

    alerts = reporting_services.evaluate_absence_alerts(
        shift=shift,
        event_date=event_date,
        as_of=timezone.make_aware(datetime.combine(event_date, time(8, 0))),
    )

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.alert_type == Alert.AlertType.ABSENCE_NOT_REGISTERED
    assert alert.student == student
    assert alert.section == section
    assert alert.target_roles == [Alert.TargetRole.SECTION_COORDINATOR]


def test_reporting_alert_surface_consistent_after_recalculation_supersedes_source():
    """
    Ties RF-JOR-006 and RF-JOR-007 together: a late-arriving exit resolves a
    ``permanencia_sin_cierre`` condition in ``attendance`` (RF-JOR-006), and
    ``sync_attendance_alerts`` reflects that supersession in this app's own
    alert surface without re-deriving the condition itself.
    """
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    cycle = AcademicCycleFactory(
        starts_on=yesterday - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    student, _section, shift = _enrolled_student(cycle)
    attendance_services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )
    attendance_services.record_attendance_event(
        student=student,
        shift=shift,
        event_date=yesterday,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(yesterday, time(7, 0))),
    )
    closure = attendance_services.close_jornada(shift=shift, event_date=yesterday)
    assert len(closure.alerts) == 1

    created, _superseded = reporting_services.sync_attendance_alerts(shift=shift)
    assert len(created) == 1
    projected = created[0]
    assert projected.alert_type == Alert.AlertType.PERMANENCIA_SIN_CIERRE

    attendance_services.record_attendance_event(
        student=student,
        shift=shift,
        event_date=yesterday,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(yesterday, time(15, 0))),
    )
    assert not AttendanceAlert.objects.filter(
        student=student, alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE, is_active=True
    ).exists()

    _created, superseded = reporting_services.sync_attendance_alerts(shift=shift)

    projected.refresh_from_db()
    assert projected.is_active is False
    assert projected in superseded
