"""
RF-JOR-001 (ventana operativa diaria) at the service boundary.

Every capture here uses fixed dates and explicit ``captured_at`` values, so
the outcome never depends on the weekday or hour the suite runs at.
"""

from datetime import UTC, date, datetime, time

import pytest
from django.utils import timezone

from apps.attendance import services
from apps.attendance.models import AttendanceEvent
from apps.audit.models import AuditEvent
from apps.common.exceptions import DomainError
from tests.factories.academic import AcademicCycleFactory, ShiftFactory
from tests.factories.attendance import (
    CaptureBatchFactory,
    ControlPointFactory,
    JornadaParametersFactory,
    ManualRegistrationReasonFactory,
)
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

WEDNESDAY = date(2026, 10, 7)
SUNDAY = date(2026, 10, 11)


def _at(day, hour, minute=0):
    """``day`` at ``hour:minute`` in the configured time zone."""
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def _parameters():
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(
        institution=shift.institution, starts_on=date(2026, 1, 12), ends_on=date(2026, 11, 13)
    )
    return JornadaParametersFactory(
        shift=shift,
        academic_cycle=cycle,
        opening_time=time(6, 0),
        entry_limit_time=time(7, 30),
        closing_time=time(16, 0),
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )


def _scan(parameters, captured_at, *, client_event_id="scan-1", operator=None, **kwargs):
    return services.record_scan_movement(
        student=kwargs.pop("student", None) or StudentFactory(),
        shift=parameters.shift,
        control_point=ControlPointFactory(campus=parameters.shift.campus),
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=captured_at,
        client_event_id=client_event_id,
        operator=operator or UserFactory(),
        **kwargs,
    )


# --------------------------------------------------------------------------- #
# RF-JOR-001 — ventana operativa diaria
# --------------------------------------------------------------------------- #


def test_scan_on_a_sunday_is_rejected_audited_and_creates_no_event():
    """RF-JOR-001: a non-school day (Sunday) is outside the operating window."""
    parameters = _parameters()

    result = _scan(parameters, _at(SUNDAY, 8, 0), client_event_id="sunday-1")

    assert isinstance(result, services.RejectedScanItem)
    assert result.reason_code == "non_school_day"
    assert "no es un dia lectivo" in result.reason
    assert not AttendanceEvent.objects.filter(client_event_id="sunday-1").exists()
    assert AuditEvent.objects.filter(
        action="attendance.event.rejected_outside_window",
        context__reason_code="non_school_day",
        context__client_event_id="sunday-1",
    ).exists()


def test_scan_before_the_opening_time_is_rejected():
    """RF-JOR-001: a scan before the configured opening time is not received."""
    parameters = _parameters()

    result = _scan(parameters, _at(WEDNESDAY, 5, 59), client_event_id="early-1")

    assert result.outcome == "rejected"
    assert result.reason_code == "outside_operating_window"
    assert not AttendanceEvent.objects.filter(client_event_id="early-1").exists()


def test_scan_after_the_closing_time_is_rejected():
    """RF-JOR-001: a scan at 23:00, after the jornada closes, is not received."""
    parameters = _parameters()

    result = _scan(parameters, _at(WEDNESDAY, 23, 0), client_event_id="late-night-1")

    assert result.outcome == "rejected"
    assert result.reason_code == "outside_operating_window"
    assert "fuera de la ventana operativa" in result.reason
    assert not AttendanceEvent.objects.filter(client_event_id="late-night-1").exists()
    assert AuditEvent.objects.filter(
        action="attendance.event.rejected_outside_window",
        context__reason_code="outside_operating_window",
    ).exists()


@pytest.mark.parametrize("hour, minute", [(6, 0), (7, 0), (16, 0)])
def test_scan_inside_the_window_on_a_school_day_is_recorded(hour, minute):
    """RF-JOR-001: opening and closing times are both inside the window."""
    parameters = _parameters()

    result = _scan(parameters, _at(WEDNESDAY, hour, minute), client_event_id=f"ok-{hour}")

    assert result.outcome == "created"
    assert result.event.event_date == WEDNESDAY


def test_window_is_evaluated_in_the_configured_time_zone():
    """
    RF-JOR-001: 21:00 UTC is 15:00 in America/Guatemala, inside a window that
    closes at 16:00 -- read as UTC it would have been rejected.
    """
    parameters = _parameters()
    captured_at = datetime.combine(WEDNESDAY, time(21, 0), tzinfo=UTC)

    result = _scan(parameters, captured_at, client_event_id="utc-1")

    assert result.outcome == "created"
    assert timezone.localtime(result.event.captured_at).hour == 15


def test_manual_registration_outside_the_window_is_rejected():
    """RF-JOR-001: a manual registration obeys the same window as a scan."""
    parameters = _parameters()

    with pytest.raises(services.OperatingWindowError) as excinfo:
        services.record_attendance_event(
            student=StudentFactory(),
            shift=parameters.shift,
            event_date=SUNDAY,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            origin=AttendanceEvent.Origin.MANUAL,
            captured_at=_at(SUNDAY, 8, 0),
            operator=UserFactory(),
            manual_reason=ManualRegistrationReasonFactory(),
        )

    assert excinfo.value.code == "non_school_day"
    assert not AttendanceEvent.objects.filter(shift=parameters.shift).exists()


def test_manual_registration_inside_the_window_is_recorded():
    """RF-JOR-001: a manual registration inside the window is accepted."""
    parameters = _parameters()

    event = services.record_attendance_event(
        student=StudentFactory(),
        shift=parameters.shift,
        event_date=WEDNESDAY,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.MANUAL,
        captured_at=_at(WEDNESDAY, 7, 10),
        operator=UserFactory(),
        manual_reason=ManualRegistrationReasonFactory(),
    )

    assert event.origin == AttendanceEvent.Origin.MANUAL


def test_scan_into_a_capture_batch_outside_the_window_is_rejected():
    """RF-JOR-001: a scan sent through a capture batch obeys the same window."""
    parameters = _parameters()
    operator = UserFactory()
    batch = CaptureBatchFactory(operator=operator)

    results = services.record_scan_batch(
        items=[
            {
                "student": StudentFactory(),
                "shift": parameters.shift,
                "control_point": ControlPointFactory(campus=parameters.shift.campus),
                "movement_type": AttendanceEvent.MovementType.ENTRY,
                "captured_at": _at(WEDNESDAY, 23, 0),
                "client_event_id": "batch-late-1",
                "capture_batch": batch,
                "transmission": AttendanceEvent.Transmission.BATCH,
            }
        ],
        operator=operator,
    )

    assert results[0].reason_code == "outside_operating_window"
    assert not batch.events.exists()


def test_jornada_parameters_reject_an_opening_time_not_before_closing():
    """RF-JOR-001: the window must open before the jornada closes."""
    parameters = _parameters()

    with pytest.raises(DomainError, match="apertura debe ser anterior"):
        services.set_jornada_parameters(
            shift=parameters.shift,
            academic_cycle=parameters.academic_cycle,
            opening_time=time(16, 0),
            entry_limit_time=time(7, 30),
            tolerance_minutes=10,
            closing_time=time(16, 0),
            duplicate_suppression_minutes=5,
            school_days=[1, 2, 3, 4, 5],
            effective_from=date(2026, 3, 2),
        )
