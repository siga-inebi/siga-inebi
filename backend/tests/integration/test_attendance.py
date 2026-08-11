"""
RF-JOR-001 — flujo cruzando dominios (academics + attendance) contra Postgres.
RF-JOR-002 — derivacion del estado diario, con matricula real de por medio.
RF-JOR-003 — precedencia entre eventos, con matricula real de por medio.
"""

from datetime import datetime, time

import pytest
from django.utils import timezone

from apps.attendance import services
from apps.attendance.models import AttendanceEvent, DayStatus, JornadaParameters
from apps.enrolments.services import create_enrolment
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    SectionFactory,
    ShiftFactory,
)
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
