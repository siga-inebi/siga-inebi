"""
RF-JOR-007 — alertas de asistencia.

All in isolation from the API layer.
"""

from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.attendance import services as attendance_services
from apps.attendance.models import AttendanceAlert
from apps.common.models import DomainError
from apps.enrolments.services import create_enrolment
from apps.reporting import services as reporting_services
from apps.reporting.models import Alert
from tests.factories.academic import AcademicCycleFactory, SectionFactory
from tests.factories.attendance import AttendanceAlertFactory
from tests.factories.identity import UserFactory
from tests.factories.reporting import AbsenceThresholdParametersFactory, ReportingAlertFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _enrolled_student(cycle):
    section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    return student, section, section.offering.shift


def _at(event_date, hour, minute):
    return timezone.make_aware(datetime.combine(event_date, time(hour, minute)))


# --------------------------------------------------------------------------- #
# RF-JOR-007 — ausencia no registrada
# --------------------------------------------------------------------------- #


def test_no_registered_entry_after_entry_limit_time_generates_absence_alert_for_section_coordinator():
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
        shift=shift, event_date=event_date, as_of=_at(event_date, 8, 0)
    )

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.alert_type == Alert.AlertType.ABSENCE_NOT_REGISTERED
    assert alert.student == student
    assert alert.section == section
    assert alert.target_roles == [Alert.TargetRole.SECTION_COORDINATOR]


def test_absence_alert_not_raised_before_entry_limit_time_elapses():
    event_date = timezone.localdate()
    cycle = AcademicCycleFactory(starts_on=event_date - timedelta(days=30))
    _student, _section, shift = _enrolled_student(cycle)
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
        shift=shift, event_date=event_date, as_of=_at(event_date, 7, 0)
    )

    assert alerts == []


# --------------------------------------------------------------------------- #
# RF-JOR-007 — proyeccion de alertas de attendance (permanencia/inconsistencia)
# --------------------------------------------------------------------------- #


def test_sync_attendance_alerts_projects_new_permanencia_sin_cierre_alert_without_reraising_detection_logic():
    shift = SectionFactory().offering.shift
    student = StudentFactory()
    event_date = timezone.localdate()
    source_alert = AttendanceAlertFactory(
        shift=shift,
        student=student,
        event_date=event_date,
        alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
        target_roles=["control_point", "section_coordinator"],
        context={"entry_event_id": "abc"},
    )

    created, superseded = reporting_services.sync_attendance_alerts(shift=shift)

    assert superseded == []
    assert len(created) == 1
    projected = created[0]
    assert projected.alert_type == Alert.AlertType.PERMANENCIA_SIN_CIERRE
    assert projected.source_attendance_alert == source_alert
    assert projected.context == {"entry_event_id": "abc"}


def test_sync_attendance_alerts_projects_inconsistencia_alert():
    shift = SectionFactory().offering.shift
    student = StudentFactory()
    event_date = timezone.localdate()
    AttendanceAlertFactory(
        shift=shift,
        student=student,
        event_date=event_date,
        alert_type=AttendanceAlert.AlertType.INCONSISTENCIA,
    )

    created, _superseded = reporting_services.sync_attendance_alerts(shift=shift)

    assert len(created) == 1
    assert created[0].alert_type == Alert.AlertType.INCONSISTENCIA


def test_sync_attendance_alerts_supersedes_local_copy_when_source_attendance_alert_is_superseded():
    shift = SectionFactory().offering.shift
    student = StudentFactory()
    event_date = timezone.localdate()
    source_alert = AttendanceAlertFactory(
        shift=shift,
        student=student,
        event_date=event_date,
        alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
    )
    created, _ = reporting_services.sync_attendance_alerts(shift=shift)
    projected = created[0]

    source_alert.is_active = False
    source_alert.save(update_fields=["is_active"])

    _created, superseded = reporting_services.sync_attendance_alerts(shift=shift)

    projected.refresh_from_db()
    assert projected.is_active is False
    assert superseded == [projected]


def test_sync_attendance_alerts_does_not_duplicate_already_projected_alert():
    shift = SectionFactory().offering.shift
    student = StudentFactory()
    event_date = timezone.localdate()
    AttendanceAlertFactory(
        shift=shift,
        student=student,
        event_date=event_date,
        alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
    )

    reporting_services.sync_attendance_alerts(shift=shift)
    created_second_run, _superseded = reporting_services.sync_attendance_alerts(shift=shift)

    assert created_second_run == []
    assert (
        Alert.objects.filter(
            student=student, alert_type=Alert.AlertType.PERMANENCIA_SIN_CIERRE, is_active=True
        ).count()
        == 1
    )


# --------------------------------------------------------------------------- #
# RF-JOR-007 — ausencias frecuentes
# --------------------------------------------------------------------------- #


def test_frequent_absences_over_threshold_generates_alert():
    today = timezone.localdate()
    event_date = today - timedelta(days=1)
    cycle = AcademicCycleFactory(
        starts_on=event_date - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    student, section, shift = _enrolled_student(cycle)
    attendance_services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[],
        effective_from=cycle.starts_on,
    )
    reporting_services.set_absence_threshold_parameters(
        shift=shift,
        academic_cycle=cycle,
        max_absences=3,
        lookback_days=3,
        effective_from=cycle.starts_on,
    )

    alerts = reporting_services.evaluate_frequent_absence_alerts(shift=shift, event_date=event_date)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.alert_type == Alert.AlertType.FREQUENT_ABSENCES
    assert alert.student == student
    assert alert.section == section
    assert alert.context["absence_count"] == 3


def test_frequent_absences_under_threshold_does_not_generate_alert():
    today = timezone.localdate()
    event_date = today - timedelta(days=1)
    cycle = AcademicCycleFactory(
        starts_on=event_date - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    _student, _section, shift = _enrolled_student(cycle)
    attendance_services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[],
        effective_from=cycle.starts_on,
    )
    reporting_services.set_absence_threshold_parameters(
        shift=shift,
        academic_cycle=cycle,
        max_absences=5,
        lookback_days=3,
        effective_from=cycle.starts_on,
    )

    alerts = reporting_services.evaluate_frequent_absence_alerts(shift=shift, event_date=event_date)

    assert alerts == []


def test_absence_threshold_is_vigencia_aware():
    threshold = AbsenceThresholdParametersFactory(max_absences=3, lookback_days=10)
    later = reporting_services.set_absence_threshold_parameters(
        shift=threshold.shift,
        academic_cycle=threshold.academic_cycle,
        max_absences=5,
        lookback_days=threshold.lookback_days,
        effective_from=threshold.effective_from + timedelta(days=30),
    )

    before = reporting_services.get_effective_absence_threshold(
        shift=threshold.shift,
        academic_cycle=threshold.academic_cycle,
        on_date=threshold.effective_from + timedelta(days=1),
    )
    after = reporting_services.get_effective_absence_threshold(
        shift=threshold.shift, academic_cycle=threshold.academic_cycle, on_date=later.effective_from
    )

    assert before == threshold
    assert before.max_absences == 3
    assert after == later
    assert after.max_absences == 5


# --------------------------------------------------------------------------- #
# RF-JOR-007 — atender una alerta
# --------------------------------------------------------------------------- #


def test_acknowledge_alert_records_actor_and_timestamp():
    alert = ReportingAlertFactory()
    actor = UserFactory()

    reporting_services.acknowledge_alert(alert=alert, actor=actor)

    alert.refresh_from_db()
    assert alert.acknowledged_by == actor
    assert alert.acknowledged_at is not None


def test_acknowledge_alert_twice_raises_domain_error():
    alert = ReportingAlertFactory()
    actor = UserFactory()
    reporting_services.acknowledge_alert(alert=alert, actor=actor)

    with pytest.raises(DomainError):
        reporting_services.acknowledge_alert(alert=alert, actor=actor)


def test_acknowledge_superseded_alert_raises_domain_error():
    alert = ReportingAlertFactory(is_active=False)
    actor = UserFactory()

    with pytest.raises(DomainError):
        reporting_services.acknowledge_alert(alert=alert, actor=actor)


# --------------------------------------------------------------------------- #
# RF-JOR-007 — evaluacion diaria combinada
# --------------------------------------------------------------------------- #


def test_evaluate_daily_alerts_covers_all_four_alert_types_in_one_call():
    today = timezone.localdate()
    event_date = today - timedelta(days=1)
    cycle = AcademicCycleFactory(
        starts_on=event_date - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    student, _section, shift = _enrolled_student(cycle)
    attendance_services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[],
        effective_from=cycle.starts_on,
    )
    reporting_services.set_absence_threshold_parameters(
        shift=shift,
        academic_cycle=cycle,
        max_absences=1,
        lookback_days=1,
        effective_from=cycle.starts_on,
    )
    AttendanceAlertFactory(
        shift=shift,
        student=student,
        event_date=event_date,
        alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
    )
    AttendanceAlertFactory(
        shift=shift,
        student=student,
        event_date=event_date,
        alert_type=AttendanceAlert.AlertType.INCONSISTENCIA,
    )

    result = reporting_services.evaluate_daily_alerts(
        shift=shift, event_date=event_date, as_of=_at(event_date, 17, 0)
    )

    generated_types = {
        alert.alert_type
        for alert in result.synced_alerts + result.absence_alerts + result.frequent_absence_alerts
    }
    assert generated_types == {
        Alert.AlertType.PERMANENCIA_SIN_CIERRE,
        Alert.AlertType.INCONSISTENCIA,
        Alert.AlertType.ABSENCE_NOT_REGISTERED,
        Alert.AlertType.FREQUENT_ABSENCES,
    }
