"""
RF-JOR-001 — parametros de jornada configurables.
RF-JOR-002 — derivacion del estado diario.
RF-JOR-003 — precedencia entre eventos.
RF-JOR-004 — cierre de jornada.
RF-JOR-005 — deteccion de inconsistencias entre fuentes.
RF-JOR-006 — recalculo ante cambios.

All in isolation from the API layer.
"""

from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.attendance import services
from apps.attendance.models import (
    AttendanceAlert,
    AttendanceEvent,
    DayStatus,
    JornadaParameters,
    RecalculationReason,
)
from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.enrolments.services import create_enrolment
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    SectionFactory,
    ShiftFactory,
)
from tests.factories.attendance import (
    AttendanceAlertFactory,
    AttendanceEventFactory,
    JornadaParametersFactory,
)
from tests.factories.identity import UserFactory
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


# --------------------------------------------------------------------------- #
# RF-JOR-004 — cierre de jornada
# --------------------------------------------------------------------------- #


def test_close_jornada_flags_permanence_without_closure():
    """
    Escenario 1 (RF-JOR-004): GIVEN un estudiante con ingreso registrado y sin
    ningun egreso, WHEN se ejecuta el cierre de la jornada, THEN el sistema
    marca el dia con la condicion de permanencia sin cierre, AND genera una
    alerta dirigida al personal del punto de control y al coordinador de aula.
    """
    parameters = JornadaParametersFactory(closing_time=time(16, 0))
    section = SectionFactory(academic_cycle=parameters.academic_cycle, shift=parameters.shift)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=parameters.academic_cycle,
        grade=section.offering.grade,
        section=section,
    )
    entry_event = AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(parameters.effective_from, 7, 0),
    )

    result = services.close_jornada(shift=parameters.shift, event_date=parameters.effective_from)

    assert len(result.alerts) == 1
    alert = result.alerts[0]
    assert alert.alert_type == AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE
    assert alert.student == student
    assert alert.section == section
    assert set(alert.target_roles) == {
        AttendanceAlert.TargetRole.CONTROL_POINT,
        AttendanceAlert.TargetRole.SECTION_COORDINATOR,
    }
    assert alert.context["entry_event_id"] == str(entry_event.public_id)
    status = next(s for s in result.statuses if s.student == student)
    assert status.permanence_without_closure is True
    assert AttendanceEvent.objects.filter(pk=entry_event.pk, is_active=True).exists()


def test_close_jornada_does_not_flag_students_with_a_matching_exit():
    parameters = JornadaParametersFactory(closing_time=time(16, 0))
    section = SectionFactory(academic_cycle=parameters.academic_cycle, shift=parameters.shift)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=parameters.academic_cycle,
        grade=section.offering.grade,
        section=section,
    )
    AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(parameters.effective_from, 7, 0),
    )
    AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(parameters.effective_from, 15, 0),
    )

    result = services.close_jornada(shift=parameters.shift, event_date=parameters.effective_from)

    assert result.alerts == []
    status = next(s for s in result.statuses if s.student == student)
    assert status.permanence_without_closure is False


# --------------------------------------------------------------------------- #
# RF-JOR-005 — deteccion de inconsistencias entre fuentes
# --------------------------------------------------------------------------- #


def test_declared_exit_without_entry_raises_inconsistency_alert():
    """
    Escenario 1 (RF-JOR-005): GIVEN un estudiante sin ingreso registrado en el
    dia, WHEN un docente lo incluye en el cierre declarado de su seccion,
    THEN el sistema conserva ambos hechos y genera una alerta de
    inconsistencia, AND identifica al docente y a la seccion como fuente de
    la declaracion.
    """
    parameters = JornadaParametersFactory()
    section = SectionFactory(academic_cycle=parameters.academic_cycle, shift=parameters.shift)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=parameters.academic_cycle,
        grade=section.offering.grade,
        section=section,
    )
    teacher = UserFactory(username="ms-lopez")

    declared_exit = services.record_attendance_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.DECLARED,
        captured_at=_at(parameters.effective_from, 15, 0),
        actor=teacher,
    )

    alerts = AttendanceAlert.objects.filter(
        student=student, alert_type=AttendanceAlert.AlertType.INCONSISTENCIA
    )
    assert alerts.count() == 1
    alert = alerts.get()
    assert alert.section == section
    assert alert.target_roles == [AttendanceAlert.TargetRole.SECTION_COORDINATOR]
    assert alert.context["declared_event_id"] == str(declared_exit.public_id)
    assert alert.context["declared_by"] == "ms-lopez"

    # Both facts remain: the declared event stays stored, and the derived
    # entry-based status is unaffected by it (no entry was ever registered).
    assert AttendanceEvent.objects.filter(pk=declared_exit.pk, is_active=True).exists()
    entry_event = services.resolve_prevailing_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
    )
    assert entry_event is None


def test_declared_exit_with_a_prior_entry_does_not_raise_an_inconsistency_alert():
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

    services.record_attendance_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.DECLARED,
        captured_at=_at(parameters.effective_from, 15, 0),
    )

    assert not AttendanceAlert.objects.filter(
        student=student, alert_type=AttendanceAlert.AlertType.INCONSISTENCIA
    ).exists()


def test_scanned_exit_without_entry_does_not_raise_an_inconsistency_alert():
    parameters = JornadaParametersFactory()
    student = StudentFactory()

    services.record_attendance_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(parameters.effective_from, 15, 0),
    )

    assert not AttendanceAlert.objects.filter(
        student=student, alert_type=AttendanceAlert.AlertType.INCONSISTENCIA
    ).exists()


# --------------------------------------------------------------------------- #
# RF-JOR-006 — recalculo ante cambios
# --------------------------------------------------------------------------- #


def _enrolled_student(cycle):
    section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    return student, section, section.offering.shift


def test_parameter_change_mid_cycle_leaves_earlier_days_on_the_old_value():
    """
    Escenario 1 (RF-JOR-006): GIVEN un ciclo escolar con estados ya derivados
    bajo un primer valor de parametros, WHEN el valor cambia con vigencia a
    partir de una fecha, THEN los dias anteriores a esa fecha conservan su
    estado original, AND los dias desde esa fecha se derivan con el nuevo
    valor.

    ``derive_day_status`` does not factor ``tolerance_minutes`` into the
    present/late boundary (only ``entry_limit_time`` does — RF-JOR-002's
    existing behavior, unchanged here), so this exercises the vigencia rule
    with ``entry_limit_time``, the field that actually drives the outcome.
    """
    today = timezone.localdate()
    cycle = AcademicCycleFactory(
        starts_on=today - timedelta(days=60), ends_on=today + timedelta(days=120)
    )
    student, _section, shift = _enrolled_student(cycle)
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 0),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )
    change_date = today + timedelta(days=10)
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=15,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=change_date,
    )

    day_before = change_date - timedelta(days=1)
    day_on_or_after = change_date
    for event_date in (day_before, day_on_or_after):
        AttendanceEventFactory(
            student=student,
            shift=shift,
            event_date=event_date,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            origin=AttendanceEvent.Origin.SCAN,
            captured_at=_at(event_date, 7, 15),
        )

    before_result = services.derive_day_status(student=student, shift=shift, event_date=day_before)
    after_result = services.derive_day_status(
        student=student, shift=shift, event_date=day_on_or_after
    )

    assert before_result.status == DayStatus.LATE
    assert after_result.status == DayStatus.PRESENT


def test_recalculate_day_does_not_mutate_original_events():
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    cycle = AcademicCycleFactory(
        starts_on=yesterday - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    student, _section, shift = _enrolled_student(cycle)
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
    entry_event = AttendanceEventFactory(
        student=student,
        shift=shift,
        event_date=yesterday,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(yesterday, 7, 0),
    )
    original_updated_at = entry_event.updated_at
    original_captured_at = entry_event.captured_at

    services.recalculate_day(
        student=student, shift=shift, event_date=yesterday, reason=RecalculationReason.LATE_EVENT
    )

    entry_event.refresh_from_db()
    assert entry_event.updated_at == original_updated_at
    assert entry_event.captured_at == original_captured_at


def test_late_arriving_exit_supersedes_permanencia_sin_cierre_alert():
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    cycle = AcademicCycleFactory(
        starts_on=yesterday - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    student, _section, shift = _enrolled_student(cycle)
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
    AttendanceEventFactory(
        student=student,
        shift=shift,
        event_date=yesterday,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(yesterday, 7, 0),
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
        captured_at=_at(yesterday, 15, 0),
    )

    alert.refresh_from_db()
    assert alert.is_active is False
    assert alert.alert_type == AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE


def test_late_arriving_entry_supersedes_inconsistencia_alert():
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    cycle = AcademicCycleFactory(
        starts_on=yesterday - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    student, _section, shift = _enrolled_student(cycle)
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
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.DECLARED,
        captured_at=_at(yesterday, 15, 0),
    )
    alert = AttendanceAlert.objects.get(
        student=student, alert_type=AttendanceAlert.AlertType.INCONSISTENCIA
    )
    assert alert.is_active is True

    services.record_attendance_event(
        student=student,
        shift=shift,
        event_date=yesterday,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(yesterday, 7, 0),
    )

    alert.refresh_from_db()
    assert alert.is_active is False


def test_recalculate_day_raises_new_permanencia_sin_cierre_alert_after_closing():
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    cycle = AcademicCycleFactory(
        starts_on=yesterday - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    student, _section, shift = _enrolled_student(cycle)
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
    assert not AttendanceAlert.objects.filter(
        student=student, alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE
    ).exists()

    services.record_attendance_event(
        student=student,
        shift=shift,
        event_date=yesterday,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(yesterday, 7, 0),
    )

    alert = AttendanceAlert.objects.get(
        student=student, alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE
    )
    assert alert.is_active is True
    assert alert.context["reason"] == RecalculationReason.LATE_EVENT


def test_recalculate_day_does_not_raise_permanencia_before_the_jornada_closes():
    """
    An entry with no exit yet is only "permanencia sin cierre" once the
    closing time has gone by — before that it just means the student is
    still inside. ``close_jornada`` gets this for free by running at closing
    time; a recalculation can land on a day still in progress.
    """
    today = timezone.localdate()
    cycle = AcademicCycleFactory(
        starts_on=today - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    student, _section, shift = _enrolled_student(cycle)
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
        event_date=today,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(today, 7, 0),
    )

    result = services.recalculate_day(
        student=student,
        shift=shift,
        event_date=today,
        reason=RecalculationReason.PARAMETERS_CHANGED,
        as_of=_at(today, 10, 0),
    )

    assert result.raised_alerts == []
    assert not AttendanceAlert.objects.filter(
        student=student, alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE
    ).exists()

    # Past the closing time the very same day does raise it.
    result = services.recalculate_day(
        student=student,
        shift=shift,
        event_date=today,
        reason=RecalculationReason.PARAMETERS_CHANGED,
        as_of=_at(today, 17, 0),
    )

    assert len(result.raised_alerts) == 1


def test_recalculate_day_is_idempotent():
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    cycle = AcademicCycleFactory(
        starts_on=yesterday - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    student, _section, shift = _enrolled_student(cycle)
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
    AttendanceEventFactory(
        student=student,
        shift=shift,
        event_date=yesterday,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(yesterday, 7, 0),
    )

    services.recalculate_day(
        student=student, shift=shift, event_date=yesterday, reason=RecalculationReason.LATE_EVENT
    )
    services.recalculate_day(
        student=student, shift=shift, event_date=yesterday, reason=RecalculationReason.LATE_EVENT
    )

    assert (
        AttendanceAlert.objects.filter(
            student=student,
            alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
            is_active=True,
        ).count()
        == 1
    )


def test_recalculate_day_always_records_audit_event_even_when_nothing_changes():
    parameters = JornadaParametersFactory()
    student = StudentFactory()

    services.recalculate_day(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        reason=RecalculationReason.LATE_EVENT,
    )

    assert AuditEvent.objects.filter(action="attendance.day.recalculated").exists()


def test_recalculate_days_for_parameters_change_only_touches_days_on_or_after_effective_from():
    today = timezone.localdate()
    cycle = AcademicCycleFactory(
        starts_on=today - timedelta(days=60), ends_on=today + timedelta(days=60)
    )
    student, _section, shift = _enrolled_student(cycle)
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
        AttendanceEventFactory(
            student=student,
            shift=shift,
            event_date=event_date,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            origin=AttendanceEvent.Origin.SCAN,
            captured_at=_at(event_date, 7, 0),
        )
        AttendanceEventFactory(
            student=student,
            shift=shift,
            event_date=event_date,
            movement_type=AttendanceEvent.MovementType.EXIT,
            origin=AttendanceEvent.Origin.SCAN,
            captured_at=_at(event_date, 15, 0),
        )
    alert_before = AttendanceAlertFactory(
        student=student,
        shift=shift,
        event_date=day_before,
        alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
    )
    alert_on_or_after = AttendanceAlertFactory(
        student=student,
        shift=shift,
        event_date=day_on_or_after,
        alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
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


def test_list_roster_day_statuses_returns_entry_for_every_active_enrolment_without_side_effects():
    cycle = AcademicCycleFactory()
    student, section, shift = _enrolled_student(cycle)
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

    statuses = services.list_roster_day_statuses(
        shift=shift, event_date=cycle.starts_on, as_of=_at(cycle.starts_on, 10, 0)
    )

    assert len(statuses) == 1
    assert statuses[0].student == student
    assert statuses[0].section == section
    assert statuses[0].status is None
    assert not AttendanceAlert.objects.exists()


def test_list_alerts_filters_by_shift_event_date_and_alert_type():
    shift = ShiftFactory()
    other_shift = ShiftFactory()
    event_date = timezone.localdate()
    matching = AttendanceAlertFactory(
        shift=shift,
        event_date=event_date,
        alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
    )
    AttendanceAlertFactory(
        shift=shift, event_date=event_date, alert_type=AttendanceAlert.AlertType.INCONSISTENCIA
    )
    AttendanceAlertFactory(
        shift=other_shift,
        event_date=event_date,
        alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
    )

    results = services.list_alerts(
        shift=shift,
        event_date=event_date,
        alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
    )

    assert list(results) == [matching]

    both_types = services.list_alerts(
        shift=shift,
        event_date=event_date,
        alert_type=[
            AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
            AttendanceAlert.AlertType.INCONSISTENCIA,
        ],
    )
    assert both_types.count() == 2


def test_derive_day_statuses_agrees_with_deriving_each_pair_on_its_own():
    """
    The batched reader exists only to cut the query fan-out, so it must
    return exactly what the per-pair reader would — precedence between
    conflicting events included.
    """
    today = timezone.localdate()
    cycle = AcademicCycleFactory(
        starts_on=today - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[],
        effective_from=cycle.starts_on,
    )
    present, late, absent = (StudentFactory() for _ in range(3))
    for student in (present, late, absent):
        create_enrolment(
            student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
        )
    days = [today - timedelta(days=offset) for offset in (1, 2)]

    services.record_attendance_event(
        student=present,
        shift=shift,
        event_date=days[0],
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(days[0], 7, 0),
    )
    services.record_attendance_event(
        student=late,
        shift=shift,
        event_date=days[0],
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.MANUAL,
        captured_at=_at(days[0], 9, 0),
    )
    # A declared event loses to the scan above under RF-JOR-003 precedence.
    services.record_attendance_event(
        student=present,
        shift=shift,
        event_date=days[0],
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.DECLARED,
        captured_at=_at(days[0], 11, 0),
    )

    as_of = _at(today, 17, 0)
    batched = services.derive_day_statuses(
        students=[present, late, absent], shift=shift, event_dates=days, as_of=as_of
    )

    for student in (present, late, absent):
        for day in days:
            expected = services.derive_day_status(
                student=student, shift=shift, event_date=day, as_of=as_of
            )
            actual = batched[(student.pk, day)]
            assert (actual is None) == (expected is None)
            if expected is not None:
                assert actual.status == expected.status
                assert actual.entry_event == expected.entry_event
                assert actual.parameters == expected.parameters

    assert batched[(present.pk, days[0])].status == DayStatus.PRESENT
    assert batched[(late.pk, days[0])].status == DayStatus.LATE
    assert batched[(absent.pk, days[0])].status == DayStatus.ABSENT_PENDING_JUSTIFICATION
