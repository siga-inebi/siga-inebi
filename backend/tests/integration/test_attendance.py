"""
RF-JOR-001 — flujo cruzando dominios (academics + attendance) contra Postgres.
RF-JOR-002 — derivacion del estado diario, con matricula real de por medio.
RF-JOR-003 — precedencia entre eventos, con matricula real de por medio.
RF-JOR-004 — cierre de jornada, con matricula real de por medio.
RF-JOR-005 — deteccion de inconsistencias entre fuentes, con matricula real de por medio.
RF-JOR-006 — recalculo ante cambios, con matricula real de por medio.
"""

from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.attendance import services
from apps.attendance.models import AttendanceAlert, AttendanceEvent, DayStatus, JornadaParameters
from apps.enrolments.services import create_enrolment
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    SectionFactory,
    ShiftFactory,
)
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.integration, pytest.mark.postgres, pytest.mark.django_db]


def test_two_jornadas_with_different_schedules_evaluate_against_their_own_parameters():
    campus = CampusFactory()
    cycle = AcademicCycleFactory(institution=campus.institution)
    morning = ShiftFactory(campus=campus)
    afternoon = ShiftFactory(campus=campus)

    services.set_jornada_parameters(
        shift=morning,
        academic_cycle=cycle,
        entry_limit_time=time(7, 0),
        tolerance_minutes=10,
        closing_time=time(13, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )
    services.set_jornada_parameters(
        shift=afternoon,
        academic_cycle=cycle,
        entry_limit_time=time(13, 30),
        tolerance_minutes=10,
        closing_time=time(18, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )

    morning_params = services.get_effective_parameters(
        shift=morning, academic_cycle=cycle, on_date=cycle.starts_on
    )
    afternoon_params = services.get_effective_parameters(
        shift=afternoon, academic_cycle=cycle, on_date=cycle.starts_on
    )

    assert morning_params.entry_limit_time == time(7, 0)
    assert afternoon_params.entry_limit_time == time(13, 30)
    assert JornadaParameters.objects.filter(academic_cycle=cycle).count() == 2


def test_derive_day_status_for_an_actively_enrolled_student():
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    parameters = services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )
    services.record_attendance_event(
        student=student,
        shift=shift,
        event_date=cycle.starts_on,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(cycle.starts_on, time(7, 0))),
    )

    result = services.derive_day_status(student=student, shift=shift, event_date=cycle.starts_on)

    assert result.status == DayStatus.PRESENT
    assert result.parameters == parameters


def test_scan_prevails_over_declared_for_an_actively_enrolled_student():
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    scan_event = services.record_attendance_event(
        student=student,
        shift=shift,
        event_date=cycle.starts_on,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(cycle.starts_on, time(15, 0))),
    )
    declared_event = services.record_attendance_event(
        student=student,
        shift=shift,
        event_date=cycle.starts_on,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.DECLARED,
        captured_at=timezone.make_aware(datetime.combine(cycle.starts_on, time(16, 0))),
    )

    prevailing = services.resolve_prevailing_event(
        student=student,
        shift=shift,
        event_date=cycle.starts_on,
        movement_type=AttendanceEvent.MovementType.EXIT,
    )

    assert prevailing == scan_event
    assert AttendanceEvent.objects.filter(pk=declared_event.pk, is_active=True).exists()


def test_close_jornada_flags_permanence_without_closure_for_an_actively_enrolled_student():
    """
    Escenario 1 (RF-JOR-004): GIVEN un estudiante con ingreso registrado y sin
    ningun egreso, WHEN se ejecuta el cierre de la jornada, THEN el sistema
    marca el dia con la condicion de permanencia sin cierre, AND genera una
    alerta dirigida al personal del punto de control y al coordinador de aula.
    """
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )
    entry_event = services.record_attendance_event(
        student=student,
        shift=shift,
        event_date=cycle.starts_on,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(cycle.starts_on, time(7, 0))),
    )

    result = services.close_jornada(shift=shift, event_date=cycle.starts_on)

    assert len(result.alerts) == 1
    alert = result.alerts[0]
    assert alert.alert_type == AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE
    assert alert.student == student
    assert alert.section == section
    assert alert.context["entry_event_id"] == str(entry_event.public_id)


def test_declared_exit_without_entry_raises_inconsistency_alert_for_an_actively_enrolled_student():
    """
    Escenario 1 (RF-JOR-005): GIVEN un estudiante sin ingreso registrado en el
    dia, WHEN un docente lo incluye en el cierre declarado de su seccion,
    THEN el sistema conserva ambos hechos y genera una alerta de
    inconsistencia, AND identifica al docente y a la seccion como fuente de
    la declaracion.
    """
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    teacher = UserFactory(username="mr-perez")

    declared_exit = services.record_attendance_event(
        student=student,
        shift=shift,
        event_date=cycle.starts_on,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.DECLARED,
        captured_at=timezone.make_aware(datetime.combine(cycle.starts_on, time(15, 0))),
        actor=teacher,
    )

    alert = AttendanceAlert.objects.get(
        student=student, alert_type=AttendanceAlert.AlertType.INCONSISTENCIA
    )
    assert alert.section == section
    assert alert.context["declared_event_id"] == str(declared_exit.public_id)
    assert alert.context["declared_by"] == "mr-perez"
    assert AttendanceEvent.objects.filter(pk=declared_exit.pk, is_active=True).exists()


# --------------------------------------------------------------------------- #
# RF-JOR-006 — recalculo ante cambios
# --------------------------------------------------------------------------- #


def test_late_event_recalculation_reconciles_permanencia_sin_cierre_end_to_end():
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    cycle = AcademicCycleFactory(
        starts_on=yesterday - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )
    services.record_attendance_event(
        student=student,
        shift=shift,
        event_date=yesterday,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(yesterday, time(7, 0))),
    )
    closure = services.close_jornada(shift=shift, event_date=yesterday)
    assert len(closure.alerts) == 1
    alert = closure.alerts[0]

    services.record_attendance_event(
        student=student,
        shift=shift,
        event_date=yesterday,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(yesterday, time(15, 0))),
    )

    alert.refresh_from_db()
    assert alert.is_active is False
    assert AttendanceAlert.objects.filter(pk=alert.pk).exists()


def test_parameter_change_recalculation_respects_vigencia_across_enrolment_and_alerts():
    today = timezone.localdate()
    cycle = AcademicCycleFactory(
        starts_on=today - timedelta(days=60), ends_on=today + timedelta(days=60)
    )
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )
    day_before = today - timedelta(days=10)
    day_on_or_after = today
    for event_date in (day_before, day_on_or_after):
        services.record_attendance_event(
            student=student,
            shift=shift,
            event_date=event_date,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            origin=AttendanceEvent.Origin.SCAN,
            captured_at=timezone.make_aware(datetime.combine(event_date, time(7, 0))),
        )
        services.record_attendance_event(
            student=student,
            shift=shift,
            event_date=event_date,
            movement_type=AttendanceEvent.MovementType.EXIT,
            origin=AttendanceEvent.Origin.SCAN,
            captured_at=timezone.make_aware(datetime.combine(event_date, time(15, 0))),
        )
    alert_before = AttendanceAlert.objects.create(
        alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
        student=student,
        shift=shift,
        section=section,
        event_date=day_before,
        target_roles=[],
        context={},
    )
    alert_on_or_after = AttendanceAlert.objects.create(
        alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
        student=student,
        shift=shift,
        section=section,
        event_date=day_on_or_after,
        target_roles=[],
        context={},
    )

    services.recalculate_days_for_parameters_change(
        shift=shift,
        academic_cycle=cycle,
        effective_from=today,
        until_date=today + timedelta(days=30),
    )

    alert_before.refresh_from_db()
    alert_on_or_after.refresh_from_db()
    assert alert_before.is_active is True
    assert alert_on_or_after.is_active is False
