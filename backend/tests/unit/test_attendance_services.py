"""
RF-JOR-001 — parametros de jornada configurables.
RF-JOR-002 — derivacion del estado diario.
RF-JOR-003 — precedencia entre eventos.
RF-JOR-004 — cierre de jornada.
RF-JOR-005 — deteccion de inconsistencias entre fuentes.
RF-JOR-006 — recalculo ante cambios.
RF-JOR-008 — consulta de presencia en tiempo real.
RF-JOR-009 — porcentaje de asistencia del ciclo.
RF-JOR-011 — advertencia sobre el uso reglamentario del indicador.
RF-ASI-001/002/004/010 — captura por escaneo, supresion de duplicados e
idempotencia.
RF-CRE-001 — emision de credencial con identificador opaco.
RF-CRE-006 — resolucion de identificador.

All in isolation from the API layer.
"""

from datetime import datetime, time, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.attendance import services
from apps.attendance.models import (
    AttendanceAlert,
    AttendanceEvent,
    DayStatus,
    JornadaParameters,
    RecalculationReason,
    StudentCredential,
)
from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment
from apps.enrolments.services import active_enrolments, create_enrolment
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    SectionFactory,
    ShiftFactory,
)
from tests.factories.attendance import (
    AttendanceAlertFactory,
    AttendanceEventFactory,
    ControlPointFactory,
    JornadaParametersFactory,
    ManualRegistrationReasonFactory,
    StudentCredentialFactory,
)
from tests.factories.identity import UserFactory
from tests.factories.people import PersonFactory
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


def test_set_jornada_parameters_is_audited_with_actor_and_vigencia():
    """
    RNF-AUD-002, camino feliz: un cambio de parametros de jornada queda en
    bitacora con el responsable y la fecha desde la que rige (vigencia).
    """
    campus = CampusFactory()
    cycle = AcademicCycleFactory(institution=campus.institution)
    shift = ShiftFactory(campus=campus)
    actor = UserFactory()

    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 0),
        tolerance_minutes=10,
        closing_time=time(13, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
        actor=actor,
    )

    event = AuditEvent.objects.latest("created_at")
    assert event.action == "attendance.jornada_parameters.set"
    assert event.actor_id == actor.id
    assert event.context["effective_from"] == str(cycle.starts_on)


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
# RNF-AUD-001 — inmutabilidad de eventos de movimiento
# --------------------------------------------------------------------------- #


def test_attendance_event_cannot_be_modified_or_deleted():
    """
    RNF-AUD-001, camino feliz e inverso: un evento ya creado no puede
    modificarse ni eliminarse por instancia, sin importar quien lo intente --
    mismo contrato que ``AuditEvent`` (RF-BIT-005).
    """
    event = AttendanceEventFactory()

    with pytest.raises(RuntimeError):
        event.delete()

    with pytest.raises(RuntimeError):
        event.movement_type = AttendanceEvent.MovementType.ENTRY
        event.save()


def test_attendance_event_cannot_be_bulk_deleted_or_updated_via_queryset():
    """
    RNF-AUD-001: ``QuerySet.delete()``/``update()`` run SQL directo y no
    pasan por los overrides de instancia, asi que el guardia de instancia no
    basta por si solo -- una operacion masiva por el manager tambien debe
    rechazarse.
    """
    event = AttendanceEventFactory()

    with pytest.raises(RuntimeError):
        AttendanceEvent.objects.all().delete()

    with pytest.raises(RuntimeError):
        AttendanceEvent.objects.all().update(movement_type=AttendanceEvent.MovementType.ENTRY)

    event.refresh_from_db()
    assert event.movement_type == AttendanceEvent.MovementType.EXIT


def test_a_correction_adds_a_new_event_instead_of_overwriting_the_original():
    """
    RNF-AUD-001: "las correcciones agregan, no sobrescriben" -- ya
    garantizado por ``record_attendance_event`` (nunca actualiza un evento
    existente) y ``resolve_prevailing_event`` (decide por precedencia sin
    tocar los eventos que pierden). Este test prueba el flujo real, no solo
    el guardia del modelo: dos eventos en conflicto para la misma
    jornada/movimiento coexisten, y el original sigue intacto y consultable.
    """
    parameters = JornadaParametersFactory()
    student = StudentFactory()

    original = services.record_attendance_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.DECLARED,
        captured_at=_at(parameters.effective_from, 7, 0),
    )
    correction = services.record_attendance_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(parameters.effective_from, 7, 5),
    )

    assert AttendanceEvent.objects.filter(pk=original.pk).exists()
    assert AttendanceEvent.objects.filter(pk=correction.pk).exists()
    assert original.pk != correction.pk

    prevailing = services.resolve_prevailing_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
    )
    assert prevailing == correction
    original.refresh_from_db()
    assert original.origin == AttendanceEvent.Origin.DECLARED


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
        operator=UserFactory(),
        manual_reason=ManualRegistrationReasonFactory(),
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


# --------------------------------------------------------------------------- #
# RF-JOR-008 — presencia en tiempo real
# --------------------------------------------------------------------------- #


def test_list_present_students_includes_entry_without_exit_and_excludes_entry_with_exit():
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    present_student = StudentFactory()
    departed_student = StudentFactory()
    create_enrolment(
        student=present_student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
    )
    create_enrolment(
        student=departed_student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
    )
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5, 6, 7],
        effective_from=cycle.starts_on,
    )
    AttendanceEventFactory(
        student=present_student,
        shift=shift,
        event_date=cycle.starts_on,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(cycle.starts_on, 7, 0),
    )
    AttendanceEventFactory(
        student=departed_student,
        shift=shift,
        event_date=cycle.starts_on,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(cycle.starts_on, 7, 0),
    )
    AttendanceEventFactory(
        student=departed_student,
        shift=shift,
        event_date=cycle.starts_on,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(cycle.starts_on, 15, 0),
    )

    present = services.list_present_students(
        shift=shift, event_date=cycle.starts_on, as_of=_at(cycle.starts_on, 16, 0)
    )

    assert [entry.student for entry in present] == [present_student]


def test_list_present_students_filters_by_grade_and_section():
    cycle = AcademicCycleFactory()
    shift = ShiftFactory(campus=CampusFactory(institution=cycle.institution))
    section_a = SectionFactory(academic_cycle=cycle, shift=shift)
    section_b = SectionFactory(academic_cycle=cycle, shift=shift)
    student_a = StudentFactory()
    student_b = StudentFactory()
    create_enrolment(
        student=student_a, academic_cycle=cycle, grade=section_a.offering.grade, section=section_a
    )
    create_enrolment(
        student=student_b, academic_cycle=cycle, grade=section_b.offering.grade, section=section_b
    )
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5, 6, 7],
        effective_from=cycle.starts_on,
    )
    for student in (student_a, student_b):
        AttendanceEventFactory(
            student=student,
            shift=shift,
            event_date=cycle.starts_on,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            origin=AttendanceEvent.Origin.SCAN,
            captured_at=_at(cycle.starts_on, 7, 0),
        )

    by_section = services.list_present_students(
        shift=shift,
        event_date=cycle.starts_on,
        section=section_a,
        as_of=_at(cycle.starts_on, 10, 0),
    )
    by_grade = services.list_present_students(
        shift=shift,
        event_date=cycle.starts_on,
        grade=section_b.offering.grade,
        as_of=_at(cycle.starts_on, 10, 0),
    )

    assert [entry.student for entry in by_section] == [student_a]
    assert [entry.student for entry in by_grade] == [student_b]


# --------------------------------------------------------------------------- #
# RF-JOR-009 — porcentaje de asistencia del ciclo
# --------------------------------------------------------------------------- #


def test_compute_attendance_percentage_counts_present_and_late_over_elapsed_school_days():
    start = timezone.localdate() - timedelta(days=30)
    day0, day1, day2 = start, start + timedelta(days=1), start + timedelta(days=2)
    cycle = AcademicCycleFactory(starts_on=start, ends_on=start + timedelta(days=200))
    section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
        effective_on=start,
    )
    shift = section.offering.shift
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5, 6, 7],
        effective_from=start,
    )
    AttendanceEventFactory(
        student=student,
        shift=shift,
        event_date=day0,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(day0, 7, 0),
    )
    AttendanceEventFactory(
        student=student,
        shift=shift,
        event_date=day1,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(day1, 8, 0),
    )
    # day2 has no entry: closed and absent, since it's 28 days in the past.

    result = services.compute_attendance_percentage(student=student, shift=shift, as_of_date=day2)

    assert result.elapsed_school_days == 3
    assert result.present_days == 1
    assert result.late_days == 1
    assert result.percentage == pytest.approx(66.67, rel=1e-2)


def test_compute_attendance_percentage_bounds_start_to_enrolment_effective_on():
    start = timezone.localdate() - timedelta(days=30)
    enrolled_from = start + timedelta(days=2)
    cycle = AcademicCycleFactory(starts_on=start, ends_on=start + timedelta(days=200))
    section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
        effective_on=enrolled_from,
    )
    shift = section.offering.shift
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5, 6, 7],
        effective_from=start,
    )
    # An entry before the enrolment started must never count.
    AttendanceEventFactory(
        student=student,
        shift=shift,
        event_date=start,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(start, 7, 0),
    )

    result = services.compute_attendance_percentage(
        student=student, shift=shift, as_of_date=enrolled_from
    )

    assert result.elapsed_school_days == 1
    assert result.present_days == 0
    assert result.percentage == 0.0


def test_compute_attendance_percentage_excludes_days_not_yet_closed():
    tomorrow = timezone.localdate() + timedelta(days=1)
    cycle = AcademicCycleFactory(starts_on=tomorrow, ends_on=tomorrow + timedelta(days=60))
    section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
        effective_on=tomorrow,
    )
    shift = section.offering.shift
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5, 6, 7],
        effective_from=tomorrow,
    )

    result = services.compute_attendance_percentage(
        student=student, shift=shift, as_of_date=tomorrow
    )

    assert result.elapsed_school_days == 0
    assert result.percentage is None


def test_compute_attendance_percentage_raises_when_student_not_enrolled_in_cycle_shift():
    cycle = AcademicCycleFactory()
    _, _, shift = _enrolled_student(cycle)
    unrelated_student = StudentFactory()

    with pytest.raises(DomainError):
        services.compute_attendance_percentage(
            student=unrelated_student, shift=shift, as_of_date=cycle.starts_on
        )


# --------------------------------------------------------------------------- #
# RF-JOR-011 — advertencia sobre el uso reglamentario del indicador
# --------------------------------------------------------------------------- #


def test_compute_attendance_percentage_carries_the_regulatory_notice():
    day = timezone.localdate() - timedelta(days=1)
    cycle = AcademicCycleFactory(starts_on=day, ends_on=day + timedelta(days=200))
    section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
        effective_on=day,
    )
    shift = section.offering.shift
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5, 6, 7],
        effective_from=day,
    )
    AttendanceEventFactory(
        student=student,
        shift=shift,
        event_date=day,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=_at(day, 7, 0),
    )

    result = services.compute_attendance_percentage(student=student, shift=shift, as_of_date=day)

    assert result.regulatory_notice == services.ATTENDANCE_PERCENTAGE_REGULATORY_NOTICE


def test_compute_attendance_percentage_carries_the_regulatory_notice_even_when_no_days_elapsed():
    """
    The report can't omit the disclaimer just because there is nothing to
    report yet — a reader who sees "0%" or a blank indicator needs the same
    warning about its informative, non-regulatory character.
    """
    tomorrow = timezone.localdate() + timedelta(days=1)
    cycle = AcademicCycleFactory(starts_on=tomorrow, ends_on=tomorrow + timedelta(days=60))
    section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
        effective_on=tomorrow,
    )
    shift = section.offering.shift
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5, 6, 7],
        effective_from=tomorrow,
    )

    result = services.compute_attendance_percentage(
        student=student, shift=shift, as_of_date=tomorrow
    )

    assert result.elapsed_school_days == 0
    assert result.regulatory_notice == services.ATTENDANCE_PERCENTAGE_REGULATORY_NOTICE


# --------------------------------------------------------------------------- #
# RF-ASI-005 — tipos de movimiento admitidos por punto de control
# --------------------------------------------------------------------------- #


def test_configure_control_point_movement_types_updates_and_audits():
    """
    Escenario 1 (RF-ASI-005): GIVEN un punto de control, WHEN un usuario
    autorizado lo configura para admitir solo egresos, THEN el punto queda
    con esa configuracion, AND el cambio queda auditado con el usuario
    responsable.
    """
    control_point = ControlPointFactory()
    actor = UserFactory()

    updated = services.configure_control_point_movement_types(
        control_point=control_point, allows_entry=False, allows_exit=True, actor=actor
    )

    updated.refresh_from_db()
    assert updated.allows_entry is False
    assert updated.allows_exit is True
    event = AuditEvent.objects.get(
        action="attendance.control_point.movement_types_configured",
        resource_identifier=str(control_point.public_id),
    )
    assert event.actor_id == actor.id
    assert event.context["allows_entry"] is False
    assert event.context["allows_exit"] is True


def test_configure_control_point_movement_types_requires_at_least_one_type_allowed():
    control_point = ControlPointFactory()

    with pytest.raises(DomainError, match="al menos un tipo"):
        services.configure_control_point_movement_types(
            control_point=control_point,
            allows_entry=False,
            allows_exit=False,
            actor=UserFactory(),
        )


def test_configure_control_point_movement_types_requires_an_actor():
    control_point = ControlPointFactory()

    with pytest.raises(DomainError, match="quien la autorizo"):
        services.configure_control_point_movement_types(
            control_point=control_point, allows_entry=True, allows_exit=False, actor=None
        )


# --------------------------------------------------------------------------- #
# RF-ASI-001/002/004/010 — captura por escaneo
# --------------------------------------------------------------------------- #


def _configure_jornada(*, shift, cycle):
    return services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5, 6, 7],
        effective_from=cycle.starts_on,
    )


def test_record_scan_movement_creates_event_with_operator_control_point_and_client_event_id():
    cycle = AcademicCycleFactory()
    student, section, shift = _enrolled_student(cycle)
    control_point = ControlPointFactory(campus=shift.campus)
    operator = UserFactory()
    _configure_jornada(shift=shift, cycle=cycle)

    result = services.record_scan_movement(
        student=student,
        shift=shift,
        control_point=control_point,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=_at(cycle.starts_on, 7, 0),
        client_event_id="scan-1",
        operator=operator,
    )

    assert result.outcome == "created"
    assert result.event.control_point == control_point
    assert result.event.operator == operator
    assert result.event.client_event_id == "scan-1"
    assert result.event.origin == AttendanceEvent.Origin.SCAN


def test_record_scan_movement_requires_operator():
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    control_point = ControlPointFactory(campus=parameters.shift.campus)

    with pytest.raises(DomainError):
        services.record_scan_movement(
            student=student,
            shift=parameters.shift,
            control_point=control_point,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            captured_at=_at(parameters.effective_from, 7, 0),
            client_event_id="scan-no-operator",
            operator=None,
        )


def test_record_scan_movement_rejects_inactive_control_point():
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    control_point = ControlPointFactory(campus=parameters.shift.campus, is_active=False)
    operator = UserFactory()

    with pytest.raises(DomainError):
        services.record_scan_movement(
            student=student,
            shift=parameters.shift,
            control_point=control_point,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            captured_at=_at(parameters.effective_from, 7, 0),
            client_event_id="scan-inactive-cp",
            operator=operator,
        )


def test_record_scan_movement_rejects_a_movement_type_the_control_point_does_not_allow():
    """
    Escenario 1 (RF-ASI-005): GIVEN un punto de control configurado solo
    para egreso, WHEN un operador intenta registrar un ingreso desde ese
    punto, THEN el sistema rechaza la operacion indicando que el punto no
    admite ingresos.
    """
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    control_point = ControlPointFactory(campus=parameters.shift.campus, allows_entry=False)
    operator = UserFactory()

    with pytest.raises(DomainError, match="no admite ingresos"):
        services.record_scan_movement(
            student=student,
            shift=parameters.shift,
            control_point=control_point,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            captured_at=_at(parameters.effective_from, 7, 0),
            client_event_id="scan-unsupported-type",
            operator=operator,
        )


def test_record_scan_movement_suppresses_duplicate_within_window_and_reports_existing():
    cycle = AcademicCycleFactory()
    student, section, shift = _enrolled_student(cycle)
    control_point = ControlPointFactory(campus=shift.campus)
    operator = UserFactory()
    _configure_jornada(shift=shift, cycle=cycle)

    first = services.record_scan_movement(
        student=student,
        shift=shift,
        control_point=control_point,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=_at(cycle.starts_on, 7, 0),
        client_event_id="scan-a",
        operator=operator,
    )
    second = services.record_scan_movement(
        student=student,
        shift=shift,
        control_point=control_point,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=_at(cycle.starts_on, 7, 3),
        client_event_id="scan-b",
        operator=operator,
    )

    assert second.outcome == "duplicate_suppressed"
    assert second.duplicate_of == first.event
    assert (
        AttendanceEvent.objects.filter(
            student=student, shift=shift, movement_type=AttendanceEvent.MovementType.ENTRY
        ).count()
        == 1
    )


def test_record_scan_movement_allows_new_movement_once_suppression_window_elapses():
    cycle = AcademicCycleFactory()
    student, section, shift = _enrolled_student(cycle)
    control_point = ControlPointFactory(campus=shift.campus)
    operator = UserFactory()
    _configure_jornada(shift=shift, cycle=cycle)

    services.record_scan_movement(
        student=student,
        shift=shift,
        control_point=control_point,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=_at(cycle.starts_on, 7, 0),
        client_event_id="scan-c",
        operator=operator,
    )
    second = services.record_scan_movement(
        student=student,
        shift=shift,
        control_point=control_point,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=_at(cycle.starts_on, 7, 10),
        client_event_id="scan-d",
        operator=operator,
    )

    assert second.outcome == "created"
    assert (
        AttendanceEvent.objects.filter(
            student=student, shift=shift, movement_type=AttendanceEvent.MovementType.ENTRY
        ).count()
        == 2
    )


def test_record_scan_movement_duplicate_suppression_ignores_operator_and_control_point():
    """
    Escenario literal de asistencia-escaneo.md: dos operadores distintos, en
    puntos de control distintos, dentro de la ventana de supresion -> se
    rechaza igual.
    """
    cycle = AcademicCycleFactory()
    student, section, shift = _enrolled_student(cycle)
    control_point_a = ControlPointFactory(campus=shift.campus)
    control_point_b = ControlPointFactory(campus=shift.campus)
    operator_a = UserFactory()
    operator_b = UserFactory()
    _configure_jornada(shift=shift, cycle=cycle)

    services.record_scan_movement(
        student=student,
        shift=shift,
        control_point=control_point_a,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=_at(cycle.starts_on, 7, 0),
        client_event_id="scan-e",
        operator=operator_a,
    )
    second = services.record_scan_movement(
        student=student,
        shift=shift,
        control_point=control_point_b,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=_at(cycle.starts_on, 7, 1),
        client_event_id="scan-f",
        operator=operator_b,
    )

    assert second.outcome == "duplicate_suppressed"


def test_record_scan_movement_rejected_duplicate_is_audited_without_creating_event():
    cycle = AcademicCycleFactory()
    student, section, shift = _enrolled_student(cycle)
    control_point = ControlPointFactory(campus=shift.campus)
    operator = UserFactory()
    _configure_jornada(shift=shift, cycle=cycle)

    services.record_scan_movement(
        student=student,
        shift=shift,
        control_point=control_point,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=_at(cycle.starts_on, 7, 0),
        client_event_id="scan-g",
        operator=operator,
    )
    services.record_scan_movement(
        student=student,
        shift=shift,
        control_point=control_point,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=_at(cycle.starts_on, 7, 2),
        client_event_id="scan-h",
        operator=operator,
    )

    assert AuditEvent.objects.filter(action="attendance.event.rejected_duplicate").exists()
    assert AttendanceEvent.objects.count() == 1


def test_record_scan_movement_replays_same_client_event_id_without_creating_duplicate():
    cycle = AcademicCycleFactory()
    student, section, shift = _enrolled_student(cycle)
    control_point = ControlPointFactory(campus=shift.campus)
    operator = UserFactory()
    _configure_jornada(shift=shift, cycle=cycle)

    first = services.record_scan_movement(
        student=student,
        shift=shift,
        control_point=control_point,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=_at(cycle.starts_on, 7, 0),
        client_event_id="scan-idempotent",
        operator=operator,
    )
    second = services.record_scan_movement(
        student=student,
        shift=shift,
        control_point=control_point,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=_at(cycle.starts_on, 7, 0),
        client_event_id="scan-idempotent",
        operator=operator,
    )

    assert second.outcome == "already_processed"
    assert second.event == first.event
    assert AttendanceEvent.objects.count() == 1


def test_record_scan_batch_processes_items_independently_when_one_item_is_invalid():
    cycle = AcademicCycleFactory()
    student, section, shift = _enrolled_student(cycle)
    control_point = ControlPointFactory(campus=shift.campus)
    operator = UserFactory()
    inactive_student = StudentFactory(is_active=False)
    _configure_jornada(shift=shift, cycle=cycle)

    results = services.record_scan_batch(
        items=[
            {
                "student": student,
                "shift": shift,
                "control_point": control_point,
                "movement_type": AttendanceEvent.MovementType.ENTRY,
                "captured_at": _at(cycle.starts_on, 7, 0),
                "client_event_id": "batch-1",
            },
            {
                "student": inactive_student,
                "shift": shift,
                "control_point": control_point,
                "movement_type": AttendanceEvent.MovementType.ENTRY,
                "captured_at": _at(cycle.starts_on, 7, 5),
                "client_event_id": "batch-2",
            },
        ],
        operator=operator,
    )

    assert results[0].outcome == "created"
    assert results[1].outcome == "rejected"
    assert results[1].client_event_id == "batch-2"
    assert AttendanceEvent.objects.count() == 1


def test_record_scan_batch_resend_of_confirmed_batch_is_a_no_op_success():
    """Escenario literal de asistencia-escaneo.md: reenvio de un lote ya confirmado."""
    cycle = AcademicCycleFactory()
    student, section, shift = _enrolled_student(cycle)
    control_point = ControlPointFactory(campus=shift.campus)
    operator = UserFactory()
    _configure_jornada(shift=shift, cycle=cycle)
    items = [
        {
            "student": student,
            "shift": shift,
            "control_point": control_point,
            "movement_type": AttendanceEvent.MovementType.ENTRY,
            "captured_at": _at(cycle.starts_on, 7, 0),
            "client_event_id": "batch-resend-1",
            "batch_id": "batch-resend",
        },
        {
            "student": student,
            "shift": shift,
            "control_point": control_point,
            "movement_type": AttendanceEvent.MovementType.EXIT,
            "captured_at": _at(cycle.starts_on, 15, 0),
            "client_event_id": "batch-resend-2",
            "batch_id": "batch-resend",
        },
    ]

    first_results = services.record_scan_batch(items=items, operator=operator)
    second_results = services.record_scan_batch(items=items, operator=operator)

    assert [result.outcome for result in first_results] == ["created", "created"]
    assert [result.outcome for result in second_results] == [
        "already_processed",
        "already_processed",
    ]
    assert AttendanceEvent.objects.count() == 2


# --------------------------------------------------------------------------- #
# RF-ASI-007 — origen y transmision como atributos independientes
# --------------------------------------------------------------------------- #


def test_record_scan_batch_keeps_origin_and_transmission_independent_and_distinguishable():
    """
    Escenario 1 (RF-ASI-007): GIVEN un operador que acumulo movimientos
    escaneados en un lote, WHEN confirma el lote, THEN cada evento conserva
    origen de escaneo y transmision por lote, AND en los reportes se
    distingue de los movimientos de origen declarado.

    ``origin`` y ``transmission`` son columnas separadas desde que existen
    (RF-ASI-002); esta prueba cierra el requerimiento verificando que un
    lote confirmado las guarda correctamente y que una consulta que agrupa
    movimientos por origen no confunde un escaneo en lote con uno declarado.
    """
    cycle = AcademicCycleFactory()
    student, section, shift = _enrolled_student(cycle)
    control_point = ControlPointFactory(campus=shift.campus)
    operator = UserFactory()
    _configure_jornada(shift=shift, cycle=cycle)

    results = services.record_scan_batch(
        items=[
            {
                "student": student,
                "shift": shift,
                "control_point": control_point,
                "movement_type": AttendanceEvent.MovementType.ENTRY,
                "captured_at": _at(cycle.starts_on, 7, 0),
                "client_event_id": "origin-batch-1",
                "batch_id": "origin-batch",
                "transmission": AttendanceEvent.Transmission.BATCH,
            },
            {
                "student": student,
                "shift": shift,
                "control_point": control_point,
                "movement_type": AttendanceEvent.MovementType.EXIT,
                "captured_at": _at(cycle.starts_on, 15, 0),
                "client_event_id": "origin-batch-2",
                "batch_id": "origin-batch",
                "transmission": AttendanceEvent.Transmission.BATCH,
            },
        ],
        operator=operator,
    )
    for result in results:
        assert result.event.origin == AttendanceEvent.Origin.SCAN
        assert result.event.transmission == AttendanceEvent.Transmission.BATCH

    declared_exit = services.record_attendance_event(
        student=student,
        shift=shift,
        event_date=cycle.starts_on,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.DECLARED,
        captured_at=_at(cycle.starts_on, 16, 0),
    )

    origins_by_id = {
        event.pk: event.origin
        for event in AttendanceEvent.objects.filter(
            student=student, shift=shift, event_date=cycle.starts_on
        )
    }
    assert origins_by_id.pop(declared_exit.pk) == AttendanceEvent.Origin.DECLARED
    assert set(origins_by_id.values()) == {AttendanceEvent.Origin.SCAN}


# --------------------------------------------------------------------------- #
# RF-ASI-012 — registro manual autorizado
# --------------------------------------------------------------------------- #


def test_record_attendance_event_manual_requires_operator():
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    reason = ManualRegistrationReasonFactory()

    with pytest.raises(DomainError):
        services.record_attendance_event(
            student=student,
            shift=parameters.shift,
            event_date=parameters.effective_from,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            origin=AttendanceEvent.Origin.MANUAL,
            captured_at=_at(parameters.effective_from, 7, 0),
            operator=None,
            manual_reason=reason,
        )


def test_record_attendance_event_manual_requires_reason():
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    operator = UserFactory()

    with pytest.raises(DomainError):
        services.record_attendance_event(
            student=student,
            shift=parameters.shift,
            event_date=parameters.effective_from,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            origin=AttendanceEvent.Origin.MANUAL,
            captured_at=_at(parameters.effective_from, 7, 0),
            operator=operator,
            manual_reason=None,
        )


def test_record_attendance_event_manual_rejects_inactive_reason():
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    operator = UserFactory()
    reason = ManualRegistrationReasonFactory(is_active=False)

    with pytest.raises(DomainError):
        services.record_attendance_event(
            student=student,
            shift=parameters.shift,
            event_date=parameters.effective_from,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            origin=AttendanceEvent.Origin.MANUAL,
            captured_at=_at(parameters.effective_from, 7, 0),
            operator=operator,
            manual_reason=reason,
        )


def test_record_attendance_event_manual_stores_operator_and_reason():
    """
    Escenario 1 (RF-ASI-012): GIVEN un estudiante que olvido su credencial,
    WHEN un usuario con permiso elevado registra su ingreso indicando el
    motivo, THEN el sistema crea un evento con origen manual, el motivo y la
    identidad del autorizador.
    """
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    operator = UserFactory()
    reason = ManualRegistrationReasonFactory(name="Olvido su credencial")

    event = services.record_attendance_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.MANUAL,
        captured_at=_at(parameters.effective_from, 7, 0),
        operator=operator,
        manual_reason=reason,
    )

    assert event.origin == AttendanceEvent.Origin.MANUAL
    assert event.operator == operator
    assert event.manual_reason == reason


def test_record_attendance_event_declared_does_not_require_operator_or_reason():
    """Manual's guard is scoped to manual origin only -- declared closures are unaffected."""
    parameters = JornadaParametersFactory()
    student = StudentFactory()

    event = services.record_attendance_event(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.DECLARED,
        captured_at=_at(parameters.effective_from, 15, 0),
    )

    assert event.operator is None
    assert event.manual_reason is None


# --------------------------------------------------------------------------- #
# RF-ASI-008 — autoridad del reloj y hora de captura
# --------------------------------------------------------------------------- #


def test_record_scan_batch_preserves_scanned_captured_at_when_batch_confirms_later():
    """
    Escenario 1 (RF-ASI-008): GIVEN un movimiento escaneado a las 12:20 dentro
    de un lote abierto, WHEN el operador confirma el lote a las 12:35, THEN
    el evento conserva 12:20 como hora de captura, AND registra 12:35 como
    hora de registro.

    ``created_at`` (``auto_now_add``) es la autoridad del reloj: se toma del
    servidor en el instante real de la escritura (la confirmacion), nunca del
    dispositivo. ``captured_at`` es el dato del escaneo individual, provisto
    por el item, y ninguna operacion de lote lo sustituye por la hora de
    confirmacion.
    """
    cycle = AcademicCycleFactory()
    student, section, shift = _enrolled_student(cycle)
    control_point = ControlPointFactory(campus=shift.campus)
    operator = UserFactory()
    _configure_jornada(shift=shift, cycle=cycle)
    scanned_at = _at(cycle.starts_on, 12, 20)

    before_confirmation = timezone.now()
    results = services.record_scan_batch(
        items=[
            {
                "student": student,
                "shift": shift,
                "control_point": control_point,
                "movement_type": AttendanceEvent.MovementType.ENTRY,
                "captured_at": scanned_at,
                "client_event_id": "clock-authority-1",
                "batch_id": "clock-authority-batch",
            }
        ],
        operator=operator,
    )
    after_confirmation = timezone.now()

    event = results[0].event
    assert event.captured_at == scanned_at
    assert before_confirmation <= event.created_at <= after_confirmation
    assert event.created_at != event.captured_at


# --------------------------------------------------------------------------- #
# RF-ASI-003 — confirmacion visual del portador
# --------------------------------------------------------------------------- #


def test_record_scan_batch_confirmation_includes_photo_name_grade_and_section():
    """
    Escenario 1 (RF-ASI-003): WHEN el operador escanea una credencial
    vigente, THEN el sistema muestra fotografia, nombre completo y grado y
    seccion del estudiante.
    """
    cycle = AcademicCycleFactory()
    student, section, shift = _enrolled_student(cycle)
    student.photo = SimpleUploadedFile("photo.jpg", b"fake-image-bytes", content_type="image/jpeg")
    student.save(update_fields=["photo"])
    control_point = ControlPointFactory(campus=shift.campus)
    operator = UserFactory()
    _configure_jornada(shift=shift, cycle=cycle)

    results = services.record_scan_batch(
        items=[
            {
                "student": student,
                "shift": shift,
                "control_point": control_point,
                "movement_type": AttendanceEvent.MovementType.ENTRY,
                "captured_at": _at(cycle.starts_on, 7, 0),
                "client_event_id": "confirmation-1",
            }
        ],
        operator=operator,
    )

    confirmation = results[0].confirmation
    assert confirmation.full_name == f"{student.person.first_name} {student.person.last_name}"
    assert confirmation.grade_name == section.offering.grade.name
    assert confirmation.section_name == section.name
    assert confirmation.photo_url is not None and "photo" in confirmation.photo_url


def test_record_scan_batch_confirmation_has_no_grade_or_section_without_active_enrolment():
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    operator = UserFactory()

    results = services.record_scan_batch(
        items=[
            {
                "student": student,
                "shift": parameters.shift,
                "control_point": control_point,
                "movement_type": AttendanceEvent.MovementType.ENTRY,
                "captured_at": _at(parameters.effective_from, 7, 0),
                "client_event_id": "confirmation-no-enrolment",
            }
        ],
        operator=operator,
    )

    confirmation = results[0].confirmation
    assert confirmation.grade_name is None
    assert confirmation.section_name is None
    assert confirmation.photo_url is None


# --------------------------------------------------------------------------- #
# RF-CRE-001 — emision de credencial con identificador opaco
# --------------------------------------------------------------------------- #


def test_issuing_a_credential_for_an_enrolled_student_creates_an_active_one():
    """
    Escenario 1 (RF-CRE-001): GIVEN un estudiante con inscripcion activa y sin
    credencial vigente, WHEN un usuario autorizado emite su credencial, THEN el
    sistema genera un identificador opaco unico y lo asocia al estudiante, AND
    la credencial queda en estado vigente.
    """
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    actor = UserFactory()

    credential = services.issue_credential(student=student, actor=actor)

    assert credential.student == student
    assert credential.status == StudentCredential.Status.ACTIVE
    assert credential.opaque_identifier
    assert (
        StudentCredential.objects.filter(
            student=student, status=StudentCredential.Status.ACTIVE
        ).count()
        == 1
    )
    assert AuditEvent.objects.filter(action="attendance.credential.issued").exists()


def test_the_opaque_identifier_does_not_encode_any_personal_data():
    """
    Escenario 2 (RF-CRE-001): GIVEN una credencial emitida, WHEN se inspecciona
    el contenido codificado en el codigo QR, THEN contiene solo el identificador
    opaco, AND no permite deducir el codigo estudiantil ni ningun dato personal
    del portador.

    Two students sharing every personal attribute are issued credentials in the
    same breath: if anything about the bearer leaked into the token, identical
    bearers would produce related tokens.
    """
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    twins = []
    for student_code in ("EST-2026-0001", "EST-2026-0002"):
        person = PersonFactory(first_name="Ana", last_name="Ramirez")
        student = StudentFactory(person=person, student_code=student_code)
        create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.offering.grade,
            section=section,
        )
        twins.append(services.issue_credential(student=student))

    first, second = twins
    assert first.opaque_identifier != second.opaque_identifier
    for credential in twins:
        payload = credential.opaque_identifier
        student = credential.student
        person = student.person
        for secret in (
            student.student_code,
            student.student_code.lower(),
            person.first_name,
            person.last_name,
            person.email,
            person.phone_number,
            str(student.public_id),
        ):
            assert secret not in payload
        # Length is the observable proof of randomness: 32 random bytes render
        # as 43 url-safe characters, far more than any derivation would need.
        assert len(payload) >= 40


def test_a_student_without_an_active_enrolment_gets_no_credential():
    student = StudentFactory()

    with pytest.raises(DomainError, match="no tiene inscripcion activa"):
        services.issue_credential(student=student)

    assert not StudentCredential.objects.filter(student=student).exists()


def test_a_second_credential_is_refused_while_one_is_still_active():
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    services.issue_credential(student=student)

    with pytest.raises(DomainError, match="ya tiene una credencial vigente"):
        services.issue_credential(student=student)

    assert StudentCredential.objects.filter(student=student).count() == 1


def test_a_colliding_identifier_is_regenerated_instead_of_failing():
    """
    The generator is injected, so a collision can be provoked deterministically:
    the first candidate is already taken and the service must retry rather than
    surface the integrity error.
    """
    cycle = AcademicCycleFactory()
    first_student, _section, _shift = _enrolled_student(cycle)
    taken = services.issue_credential(student=first_student).opaque_identifier

    second_section = SectionFactory(academic_cycle=cycle)
    second_student = StudentFactory()
    create_enrolment(
        student=second_student,
        academic_cycle=cycle,
        grade=second_section.offering.grade,
        section=second_section,
    )
    candidates = iter([taken, "a-free-identifier"])

    credential = services.issue_credential(
        student=second_student, generate_identifier=lambda: next(candidates)
    )

    assert credential.opaque_identifier == "a-free-identifier"


# --------------------------------------------------------------------------- #
# RF-CRE-002 — contenido visible de la credencial
# --------------------------------------------------------------------------- #


def test_resolve_credential_print_content_returns_name_photo_grade_section_cycle_institution():
    """
    Escenario 1 (RF-CRE-002): GIVEN un estudiante con credencial vigente, WHEN
    un usuario autorizado genera el material imprimible, THEN el documento
    incluye nombre, fotografia, grado y seccion, ciclo e institucion, AND no
    incluye informacion de salud ni datos de contacto de la familia.
    """
    cycle = AcademicCycleFactory()
    student, section, _shift = _enrolled_student(cycle)
    student.photo = SimpleUploadedFile("photo.jpg", b"fake-image-bytes", content_type="image/jpeg")
    student.save(update_fields=["photo"])
    services.issue_credential(student=student)

    content = services.resolve_credential_print_content(student=student)

    assert content.full_name == f"{student.person.first_name} {student.person.last_name}"
    assert content.grade_name == section.offering.grade.name
    assert content.section_name == section.name
    assert content.academic_cycle_name == cycle.name
    assert content.institution_name == cycle.institution.name
    assert content.photo_url is not None and "photo" in content.photo_url


def test_resolve_credential_print_content_requires_an_active_credential():
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)

    with pytest.raises(DomainError, match="no tiene una credencial vigente"):
        services.resolve_credential_print_content(student=student)


def test_resolve_credential_print_content_requires_active_enrolment():
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    services.issue_credential(student=student)
    student.enrolments.update(status=Enrolment.EnrolmentStatus.WITHDRAWN)

    with pytest.raises(DomainError, match="no tiene inscripcion activa"):
        services.resolve_credential_print_content(student=student)


def test_resolve_credential_print_content_rejects_a_revoked_credential():
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    StudentCredentialFactory(student=student, status=StudentCredential.Status.REVOKED)

    with pytest.raises(DomainError, match="no tiene una credencial vigente"):
        services.resolve_credential_print_content(student=student)


# --------------------------------------------------------------------------- #
# RF-CRE-003 — vigencia y revocacion
# --------------------------------------------------------------------------- #


def test_revoke_credential_records_reason_and_revoker_and_rejects_reuse():
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    issued = services.issue_credential(student=student)
    actor = UserFactory()

    revoked = services.revoke_credential(student=student, reason="Extravío", actor=actor)

    assert revoked.pk == issued.pk
    assert revoked.status == StudentCredential.Status.REVOKED
    assert revoked.revocation_reason == "Extravío"
    assert revoked.revoked_by == actor
    with pytest.raises(DomainError, match="revocada"):
        services.resolve_credential(opaque_identifier=issued.opaque_identifier)


def test_revoke_credential_requires_a_reason():
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)

    with pytest.raises(DomainError, match="motivo"):
        services.revoke_credential(student=student, reason="", actor=UserFactory())


def test_revoke_credential_requires_an_actor():
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    services.issue_credential(student=student)

    with pytest.raises(DomainError, match="autorizo"):
        services.revoke_credential(student=student, reason="Extravío", actor=None)


def test_revoke_credential_without_an_active_one_is_rejected():
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)

    with pytest.raises(DomainError, match="credencial vigente"):
        services.revoke_credential(student=student, reason="Extravío", actor=UserFactory())


def test_revoke_credential_twice_is_rejected_the_second_time():
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    services.issue_credential(student=student)
    actor = UserFactory()
    services.revoke_credential(student=student, reason="Extravío", actor=actor)

    with pytest.raises(DomainError, match="credencial vigente"):
        services.revoke_credential(student=student, reason="Duplicada", actor=actor)


# --------------------------------------------------------------------------- #
# RF-CRE-005 — persistencia de los movimientos ante revocacion
# --------------------------------------------------------------------------- #


def test_revoking_a_credential_does_not_alter_past_attendance_events_or_day_status():
    """
    Escenario 1 (RF-CRE-005): GIVEN un estudiante con movimientos de
    asistencia registrados durante la semana, WHEN se revoca su credencial
    por extravio, THEN los movimientos previos permanecen sin cambios, AND
    el estado diario derivado de esos movimientos tampoco cambia.

    Nada nuevo que programar: ``AttendanceEvent`` no tiene relacion alguna
    con ``StudentCredential`` (ni FK ni señal) y ``revoke_credential`` solo
    muta la fila de la credencial, asi que esto ya se cumple por diseño,
    igual que RF-CRE-004. Esta prueba deja esa garantia verificable.
    """
    today = timezone.localdate()
    cycle = AcademicCycleFactory(starts_on=today - timedelta(days=30))
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
    services.issue_credential(student=student)

    event_dates = [today - timedelta(days=offset) for offset in (4, 3, 2, 1)]
    events = [
        AttendanceEventFactory(
            student=student,
            shift=shift,
            event_date=event_date,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            captured_at=timezone.make_aware(datetime.combine(event_date, time(7, 0))),
        )
        for event_date in event_dates
    ]
    events_before = {
        event.pk: (event.event_date, event.movement_type, event.captured_at, event.is_active)
        for event in events
    }
    day_statuses_before = {
        key: (result.status if result else None, result.entry_event.pk if result else None)
        for key, result in services.derive_day_statuses(
            students=[student], shift=shift, event_dates=event_dates
        ).items()
    }

    services.revoke_credential(student=student, reason="Extravío", actor=UserFactory())

    events_after = {
        event.pk: (event.event_date, event.movement_type, event.captured_at, event.is_active)
        for event in AttendanceEvent.objects.filter(pk__in=events_before)
    }
    assert events_after == events_before
    day_statuses_after = {
        key: (result.status if result else None, result.entry_event.pk if result else None)
        for key, result in services.derive_day_statuses(
            students=[student], shift=shift, event_dates=event_dates
        ).items()
    }
    assert day_statuses_after == day_statuses_before
# RF-CRE-004 — reposicion sin perdida de historial
# --------------------------------------------------------------------------- #


def test_reissuing_after_revocation_generates_a_new_identifier_and_keeps_the_old_row():
    """
    Escenario 1 (RF-CRE-004): GIVEN un estudiante cuya credencial fue
    revocada, WHEN un usuario autorizado emite la reposicion, THEN el
    sistema genera un identificador opaco distinto del anterior, AND el
    historial de credenciales del estudiante conserva la credencial
    revocada.

    Nada nuevo que programar: la restriccion unica de la base de datos
    (``unique_active_student_credential``) solo exige una credencial
    ACTIVA a la vez, no una por estudiante en total, asi que
    ``issue_credential`` ya acepta emitir de nuevo apenas la anterior deja
    de estar activa. Esta prueba cierra el requerimiento sobre ese
    comportamiento existente (RF-CRE-001/003), no agrega logica nueva.
    """
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    original = services.issue_credential(student=student)
    admin = UserFactory()
    revoked = services.revoke_credential(student=student, reason="Extravio", actor=admin)

    reissued = services.issue_credential(student=student)

    assert reissued.opaque_identifier != original.opaque_identifier
    assert reissued.status == StudentCredential.Status.ACTIVE

    revoked.refresh_from_db()
    assert revoked.status == StudentCredential.Status.REVOKED
    assert revoked.revocation_reason == "Extravio"
    assert revoked.revoked_by == admin
    assert StudentCredential.objects.filter(student=student).count() == 2


# --------------------------------------------------------------------------- #
# RF-CRE-006 — resolucion de identificador
# --------------------------------------------------------------------------- #


def test_an_unknown_identifier_is_rejected_without_naming_any_student():
    """
    Escenario 1 (RF-CRE-006): GIVEN un codigo QR que no corresponde a ninguna
    credencial emitida, WHEN un operador lo escanea, THEN el sistema informa que
    la credencial no es reconocida, AND no muestra informacion de ningun
    estudiante.
    """
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    issued = services.issue_credential(student=student)

    with pytest.raises(DomainError) as failure:
        services.resolve_credential(opaque_identifier="not-a-real-token")

    message = str(failure.value)
    assert "no es reconocida" in message
    # The rejection is a fact about the credential, never about a person: an
    # outsider probing the endpoint learns nothing about who exists.
    assert student.student_code not in message
    assert str(student.public_id) not in message
    assert issued.opaque_identifier not in message


def test_a_withdrawn_students_credential_resolves_to_a_rejection():
    """
    Escenario 2 (RF-CRE-006): GIVEN una credencial vigente cuyo estudiante fue
    retirado del establecimiento, WHEN un operador la escanea, THEN el sistema
    rechaza el movimiento indicando que el estudiante no tiene inscripcion
    activa.
    """
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    credential = services.issue_credential(student=student)

    enrolment = active_enrolments(student=student).get()
    enrolment.status = Enrolment.EnrolmentStatus.WITHDRAWN
    enrolment.save(update_fields=["status"])

    with pytest.raises(DomainError, match="no tiene inscripcion activa"):
        services.resolve_credential(opaque_identifier=credential.opaque_identifier)

    # The credential itself is untouched: withdrawal is an enrolment fact, and
    # rewriting the credential would erase why it stopped working.
    credential.refresh_from_db()
    assert credential.status == StudentCredential.Status.ACTIVE


def test_a_valid_identifier_resolves_to_its_bearer_and_placement():
    cycle = AcademicCycleFactory()
    student, section, _shift = _enrolled_student(cycle)
    credential = services.issue_credential(student=student)

    resolution = services.resolve_credential(opaque_identifier=credential.opaque_identifier)

    assert resolution.student == student
    assert resolution.credential == credential
    assert resolution.enrolment.section == section


def test_a_revoked_credential_no_longer_resolves():
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    credential = services.issue_credential(student=student)
    credential.status = StudentCredential.Status.REVOKED
    credential.save(update_fields=["status"])

    with pytest.raises(DomainError, match="fue revocada"):
        services.resolve_credential(opaque_identifier=credential.opaque_identifier)


def test_the_scan_subject_resolves_from_either_a_credential_or_a_student_code():
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    credential = services.issue_credential(student=student)

    by_credential = services.resolve_scan_subject(
        credential_identifier=credential.opaque_identifier
    )
    by_code = services.resolve_scan_subject(student_code=student.student_code)

    assert by_credential == student
    assert by_code == student

    with pytest.raises(DomainError, match="no es reconocida"):
        services.resolve_scan_subject(credential_identifier="unknown-token")
    with pytest.raises(DomainError, match="No existe estudiante"):
        services.resolve_scan_subject(student_code="EST-DOES-NOT-EXIST")


# --------------------------------------------------------------------------- #
# RNF-SEG-003 -- registro de intentos de escaneo rechazados
# --------------------------------------------------------------------------- #


def test_an_unrecognized_credential_is_audited_without_naming_any_student():
    """
    RNF-SEG-003, camino feliz: un codigo invalido queda registrado en la
    bitacora. La respuesta al operador sigue sin nombrar a nadie (verificado
    arriba); el asiento interno tampoco puede, porque en este caso el sistema
    mismo no sabe de quien se trataba.
    """
    operator = UserFactory()

    with pytest.raises(DomainError):
        services.resolve_credential(opaque_identifier="not-a-real-token", actor=operator)

    event = AuditEvent.objects.latest("created_at")
    assert event.action == "attendance.credential.resolution_rejected"
    assert event.actor_id == operator.id
    assert event.context["reason"] == "unrecognized_credential"
    assert "student_id" not in event.context


def test_a_revoked_credential_rejection_is_audited_with_the_student():
    """RNF-SEG-003: "credencial no vigente" -- el sistema si sabe de quien, y lo registra."""
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    credential = services.issue_credential(student=student)
    credential.status = StudentCredential.Status.REVOKED
    credential.save(update_fields=["status"])
    operator = UserFactory()

    with pytest.raises(DomainError):
        services.resolve_credential(opaque_identifier=credential.opaque_identifier, actor=operator)

    event = AuditEvent.objects.latest("created_at")
    assert event.action == "attendance.credential.resolution_rejected"
    assert event.context["reason"] == "revoked_credential"
    assert event.context["student_id"] == student.pk


def test_an_unregistered_student_code_rejection_is_audited():
    """RNF-SEG-003: "estudiante no registrado" via el codigo de respaldo."""
    operator = UserFactory()

    with pytest.raises(DomainError):
        services.resolve_scan_subject(student_code="EST-DOES-NOT-EXIST", actor=operator)

    event = AuditEvent.objects.latest("created_at")
    assert event.action == "attendance.credential.resolution_rejected"
    assert event.actor_id == operator.id
    assert event.context["reason"] == "unregistered_student_code"


# --------------------------------------------------------------------------- #
# Consistencia entre las dos vias de identificacion del sujeto escaneado
# --------------------------------------------------------------------------- #


def test_both_identification_paths_refuse_a_student_without_active_enrolment():
    """
    La regla de inscripcion activa no depende de por donde entro el escaneo.
    Antes vivia solo en la ruta de credencial, asi que la misma operacion se
    aceptaba o se rechazaba segun como el operador hubiera identificado a la
    persona.
    """
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    credential = services.issue_credential(student=student)

    enrolment = active_enrolments(student=student).get()
    enrolment.status = Enrolment.EnrolmentStatus.WITHDRAWN
    enrolment.save(update_fields=["status"])

    with pytest.raises(DomainError, match="no tiene inscripcion activa"):
        services.resolve_scan_subject(credential_identifier=credential.opaque_identifier)
    with pytest.raises(DomainError, match="no tiene inscripcion activa"):
        services.resolve_scan_subject(student_code=student.student_code)


def test_the_credential_rejection_still_refuses_to_name_the_bearer():
    """
    Compartir la regla no comparte la redaccion. RF-CRE-006 prohibe revelar al
    estudiante al rechazar, asi que la ruta de credencial sigue hablando del
    portador; la de codigo puede devolver el codigo que el operador ya escribio.
    """
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    credential = services.issue_credential(student=student)

    enrolment = active_enrolments(student=student).get()
    enrolment.status = Enrolment.EnrolmentStatus.WITHDRAWN
    enrolment.save(update_fields=["status"])

    with pytest.raises(DomainError) as by_credential:
        services.resolve_scan_subject(credential_identifier=credential.opaque_identifier)
    with pytest.raises(DomainError) as by_code:
        services.resolve_scan_subject(student_code=student.student_code)

    assert student.student_code not in str(by_credential.value)
    assert str(student.public_id) not in str(by_credential.value)
    assert student.student_code in str(by_code.value)


def test_an_enrolled_student_still_resolves_by_either_path():
    """La regla rechaza al retirado sin estorbar al inscrito."""
    cycle = AcademicCycleFactory()
    student, _section, _shift = _enrolled_student(cycle)
    credential = services.issue_credential(student=student)

    by_credential = services.resolve_scan_subject(
        credential_identifier=credential.opaque_identifier
    )
    by_code = services.resolve_scan_subject(student_code=student.student_code)

    assert by_credential == student
    assert by_code == student
