"""
RF-JOR-001 — parametros de jornada configurables.
RF-JOR-002 — derivacion del estado diario.
RF-JOR-003 — precedencia entre eventos.

All three in isolation from the API layer.
"""

from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.attendance import services
from apps.attendance.models import AttendanceEvent, DayStatus, JornadaParameters
from apps.common.models import DomainError
from tests.factories.academic import AcademicCycleFactory, CampusFactory, ShiftFactory
from tests.factories.attendance import AttendanceEventFactory, JornadaParametersFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_two_jornadas_with_different_schedules_evaluate_independently():
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


def test_set_jornada_parameters_never_mutates_prior_versions():
    parameters = JornadaParametersFactory(entry_limit_time=time(7, 0))

    services.set_jornada_parameters(
        shift=parameters.shift,
        academic_cycle=parameters.academic_cycle,
        entry_limit_time=time(7, 15),
        tolerance_minutes=parameters.tolerance_minutes,
        closing_time=parameters.closing_time,
        duplicate_suppression_minutes=parameters.duplicate_suppression_minutes,
        school_days=parameters.school_days,
        effective_from=parameters.effective_from + timedelta(days=30),
    )

    parameters.refresh_from_db()
    assert parameters.entry_limit_time == time(7, 0)
    assert JornadaParameters.objects.filter(shift=parameters.shift).count() == 2


def test_get_effective_parameters_picks_the_latest_version_on_or_before_the_date():
    parameters = JornadaParametersFactory(entry_limit_time=time(7, 0))
    later = services.set_jornada_parameters(
        shift=parameters.shift,
        academic_cycle=parameters.academic_cycle,
        entry_limit_time=time(7, 15),
        tolerance_minutes=parameters.tolerance_minutes,
        closing_time=parameters.closing_time,
        duplicate_suppression_minutes=parameters.duplicate_suppression_minutes,
        school_days=parameters.school_days,
        effective_from=parameters.effective_from + timedelta(days=30),
    )

    before = services.get_effective_parameters(
        shift=parameters.shift,
        academic_cycle=parameters.academic_cycle,
        on_date=parameters.effective_from + timedelta(days=1),
    )
    after = services.get_effective_parameters(
        shift=parameters.shift,
        academic_cycle=parameters.academic_cycle,
        on_date=later.effective_from,
    )

    assert before == parameters
    assert after == later


def test_get_effective_parameters_raises_when_none_configured():
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.institution)

    with pytest.raises(DomainError):
        services.get_effective_parameters(
            shift=shift, academic_cycle=cycle, on_date=cycle.starts_on
        )


def test_set_jornada_parameters_rejects_mismatched_institution():
    shift = ShiftFactory()
    other_cycle = AcademicCycleFactory()

    with pytest.raises(DomainError):
        services.set_jornada_parameters(
            shift=shift,
            academic_cycle=other_cycle,
            entry_limit_time=time(7, 0),
            tolerance_minutes=10,
            closing_time=time(13, 0),
            duplicate_suppression_minutes=5,
            school_days=[1, 2, 3, 4, 5],
            effective_from=other_cycle.starts_on,
        )


def test_resolve_academic_cycle_for_finds_the_cycle_covering_the_date():
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.institution)

    resolved = services.resolve_academic_cycle_for(shift=shift, event_date=cycle.starts_on)

    assert resolved == cycle


# --------------------------------------------------------------------------- #
# RF-JOR-003 — precedencia entre eventos. resolve_prevailing_event is also
# what RF-JOR-002's derivation reads to pick "the" entry/exit event when more
# than one exists.
# --------------------------------------------------------------------------- #


def _at(event_date, hour, minute):
    return timezone.make_aware(datetime.combine(event_date, time(hour, minute)))


def test_escaneo_prevalece_sobre_declaracion():
    """
    Escenario 1 (RF-JOR-003): GIVEN un estudiante con un egreso de origen
    escaneado y un egreso de origen declarado para la misma jornada, WHEN se
    deriva su estado del dia, THEN el estado se calcula con el evento de
    origen escaneado, AND el evento declarado permanece almacenado y
    consultable.
    """
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    scan_exit = AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(parameters.effective_from, 15, 0),
    )
    declared_exit = AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.DECLARED,
        captured_at=_at(parameters.effective_from, 16, 0),
    )

    prevailing = services.resolve_prevailing_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.EXIT,
    )

    assert prevailing == scan_exit
    assert AttendanceEvent.objects.filter(pk=declared_exit.pk, is_active=True).exists()


def test_resolve_prevailing_event_prefers_scan_over_other_origins():
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    scan_event = AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(parameters.effective_from, 15, 0),
    )
    AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.DECLARED,
        captured_at=_at(parameters.effective_from, 16, 0),
    )

    prevailing = services.resolve_prevailing_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.EXIT,
    )

    assert prevailing == scan_event


def test_resolve_prevailing_event_picks_latest_captured_at_within_same_origin():
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(parameters.effective_from, 7, 0),
    )
    latest = AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(parameters.effective_from, 7, 15),
    )

    prevailing = services.resolve_prevailing_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
    )

    assert prevailing == latest


def test_resolve_prevailing_event_returns_none_when_no_events_match():
    parameters = JornadaParametersFactory()
    student = StudentFactory()

    prevailing = services.resolve_prevailing_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
    )

    assert prevailing is None


def test_record_attendance_event_rejects_inactive_student():
    parameters = JornadaParametersFactory()
    student = StudentFactory(is_active=False)

    with pytest.raises(DomainError):
        services.record_attendance_event(
            student=student,
            shift=parameters.shift,
            event_date=parameters.effective_from,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            origin=AttendanceEvent.Origin.SCAN,
            captured_at=_at(parameters.effective_from, 7, 0),
        )


# --------------------------------------------------------------------------- #
# RF-JOR-002 — derivacion del estado diario
# --------------------------------------------------------------------------- #


def test_entry_before_limit_is_present():
    parameters = JornadaParametersFactory(entry_limit_time=time(7, 30))
    student = StudentFactory()
    entry_event = AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(parameters.effective_from, 7, 0),
    )

    result = services.derive_day_status(
        student=student, shift=parameters.shift, event_date=parameters.effective_from
    )

    assert result.status == DayStatus.PRESENT
    assert result.entry_event == entry_event


def test_entry_after_limit_within_tolerance_is_late():
    parameters = JornadaParametersFactory(entry_limit_time=time(7, 30), tolerance_minutes=10)
    student = StudentFactory()
    AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(parameters.effective_from, 7, 35),
    )

    result = services.derive_day_status(
        student=student, shift=parameters.shift, event_date=parameters.effective_from
    )

    assert result.status == DayStatus.LATE


def test_no_events_after_closing_time_is_absent_pending_justification():
    parameters = JornadaParametersFactory(closing_time=time(16, 0))
    student = StudentFactory()

    result = services.derive_day_status(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        as_of=_at(parameters.effective_from, 16, 1),
    )

    assert result.status == DayStatus.ABSENT_PENDING_JUSTIFICATION
    assert result.entry_event is None


def test_no_events_before_closing_time_has_no_final_status_yet():
    parameters = JornadaParametersFactory(closing_time=time(16, 0))
    student = StudentFactory()

    result = services.derive_day_status(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        as_of=_at(parameters.effective_from, 10, 0),
    )

    assert result is None
