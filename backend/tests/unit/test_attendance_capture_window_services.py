"""
RF-JOR-001 (ventana operativa diaria) and RF-AUT-005 (vencimiento del turno de
captura) at the service boundary.

Every capture here uses fixed dates and explicit ``captured_at`` values, so
the outcome never depends on the weekday or hour the suite runs at.
"""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.attendance import services
from apps.attendance.models import AttendanceEvent, CaptureBatch
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
        movement_type=kwargs.pop("movement_type", AttendanceEvent.MovementType.ENTRY),
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


EXIT = AttendanceEvent.MovementType.EXIT


@pytest.mark.parametrize("hour, minute", [(16, 30), (17, 0)])
def test_exit_within_the_grace_after_closing_is_recorded(hour, minute):
    """
    RF-JOR-001: an exit is received until ``closing_time`` plus
    ``ATTENDANCE_EXIT_GRACE_MINUTES`` (60 by default), the limit included.
    """
    parameters = _parameters()

    result = _scan(
        parameters,
        _at(WEDNESDAY, hour, minute),
        client_event_id=f"grace-{hour}",
        movement_type=EXIT,
    )

    assert result.outcome == "created"
    assert result.event.movement_type == EXIT


def test_exit_beyond_the_grace_after_closing_is_rejected():
    """RF-JOR-001: an exit one minute past closing plus the grace is not received."""
    parameters = _parameters()

    result = _scan(
        parameters, _at(WEDNESDAY, 17, 1), client_event_id="grace-over", movement_type=EXIT
    )

    assert result.outcome == "rejected"
    assert result.reason_code == "outside_operating_window"
    assert not AttendanceEvent.objects.filter(client_event_id="grace-over").exists()


def test_entry_after_closing_is_rejected_even_within_the_exit_grace():
    """RF-JOR-001: the exit grace never extends the window for entries."""
    parameters = _parameters()

    result = _scan(parameters, _at(WEDNESDAY, 16, 30), client_event_id="entry-in-grace")

    assert result.reason_code == "outside_operating_window"
    assert not AttendanceEvent.objects.filter(client_event_id="entry-in-grace").exists()


def test_exit_on_a_non_school_day_is_rejected_despite_the_grace():
    """RF-JOR-001: the school-day rule applies to exits exactly as to entries."""
    parameters = _parameters()

    result = _scan(
        parameters, _at(SUNDAY, 16, 30), client_event_id="sunday-exit", movement_type=EXIT
    )

    assert result.reason_code == "non_school_day"


@pytest.mark.parametrize(
    "grace_minutes, outcome",
    [(0, "rejected"), (15, "rejected"), (30, "created")],
)
def test_exit_grace_is_configurable(grace_minutes, outcome):
    """RF-JOR-001: ``ATTENDANCE_EXIT_GRACE_MINUTES`` sets the exit grace."""
    parameters = _parameters()

    with override_settings(ATTENDANCE_EXIT_GRACE_MINUTES=grace_minutes):
        result = _scan(
            parameters,
            _at(WEDNESDAY, 16, 30),
            client_event_id=f"configured-grace-{grace_minutes}",
            movement_type=EXIT,
        )

    assert result.outcome == outcome


def test_manual_exit_within_the_grace_is_recorded():
    """RF-JOR-001: a manual exit gets the same grace as a scanned one."""
    parameters = _parameters()

    event = services.record_attendance_event(
        student=StudentFactory(),
        shift=parameters.shift,
        event_date=WEDNESDAY,
        movement_type=EXIT,
        origin=AttendanceEvent.Origin.MANUAL,
        captured_at=_at(WEDNESDAY, 16, 45),
        operator=UserFactory(),
        manual_reason=ManualRegistrationReasonFactory(),
    )

    assert event.movement_type == EXIT


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


# --------------------------------------------------------------------------- #
# RF-AUT-005 — vencimiento del turno de captura
# --------------------------------------------------------------------------- #


def test_scan_into_an_expired_capture_batch_is_rejected_and_the_batch_closed_and_audited():
    """
    RF-AUT-005: a scan sent after the batch's assigned time closes the batch
    (lazily, ADR-0009), audits the closure and is itself rejected.
    """
    parameters = _parameters()
    operator = UserFactory()
    batch = CaptureBatchFactory(operator=operator, expires_at=timezone.now() - timedelta(minutes=1))

    result = _scan(
        parameters,
        _at(WEDNESDAY, 7, 0),
        client_event_id="expired-1",
        operator=operator,
        capture_batch=batch,
    )

    assert result.outcome == "rejected"
    assert result.reason_code == "capture_batch_expired"
    assert not AttendanceEvent.objects.filter(client_event_id="expired-1").exists()
    batch.refresh_from_db()
    assert batch.status == CaptureBatch.Status.EXPIRED
    assert batch.closed_at is not None
    assert (
        AuditEvent.objects.filter(
            action="attendance.capture_batch.expired", resource_identifier=str(batch.public_id)
        ).count()
        == 1
    )
    assert AuditEvent.objects.filter(
        action="attendance.event.rejected_capture_batch_expired",
        context__reason_code="capture_batch_expired",
    ).exists()


def test_scan_into_a_capture_batch_within_its_assigned_time_is_recorded():
    """RF-AUT-005: a batch whose assigned time has not elapsed keeps accepting scans."""
    parameters = _parameters()
    operator = UserFactory()
    batch = CaptureBatchFactory(
        operator=operator, expires_at=timezone.now() + timedelta(minutes=30)
    )

    result = _scan(
        parameters,
        _at(WEDNESDAY, 7, 0),
        client_event_id="current-1",
        operator=operator,
        capture_batch=batch,
    )

    assert result.outcome == "created"
    assert result.event.capture_batch_id == batch.pk
    batch.refresh_from_db()
    assert batch.status == CaptureBatch.Status.OPEN


def test_open_capture_batch_assigns_the_configured_duration(settings):
    """RF-AUT-005: the assigned time is fixed when the turn opens."""
    settings.ATTENDANCE_CAPTURE_TURN_MINUTES = 45
    before = timezone.now()

    batch = services.open_capture_batch(operator=UserFactory())

    assert before + timedelta(minutes=45) <= batch.expires_at
    assert batch.expires_at <= timezone.now() + timedelta(minutes=45)


def test_recovering_an_expired_batch_closes_it_and_a_new_open_starts_a_fresh_one():
    """
    RF-AUT-005: recovery (``capture-batches/current``) never resumes an
    expired turn; it closes it on that read, and the next open starts anew.
    """
    operator = UserFactory()
    expired = CaptureBatchFactory(
        operator=operator, expires_at=timezone.now() - timedelta(seconds=1)
    )

    assert services.recover_open_capture_batch(operator=operator) is None
    expired.refresh_from_db()
    assert expired.status == CaptureBatch.Status.EXPIRED

    fresh = services.open_capture_batch(operator=operator)
    assert fresh.pk != expired.pk
    assert fresh.status == CaptureBatch.Status.OPEN


def test_a_batch_without_assigned_time_falls_back_to_created_at_plus_duration(settings):
    """RF-AUT-005: batches opened before ``expires_at`` existed still expire."""
    settings.ATTENDANCE_CAPTURE_TURN_MINUTES = 60
    batch = CaptureBatchFactory(expires_at=None)

    assert services.capture_batch_expires_at(batch) == batch.created_at + timedelta(minutes=60)
    assert not services.expire_capture_batch_if_due(capture_batch=batch)
    assert services.expire_capture_batch_if_due(
        capture_batch=batch, now=batch.created_at + timedelta(minutes=60)
    )


def test_confirming_an_expired_batch_is_rejected_but_its_expiry_is_kept():
    """RF-AUT-005: the expiry closure survives the rejected confirmation."""
    operator = UserFactory()
    batch = CaptureBatchFactory(operator=operator, expires_at=timezone.now() - timedelta(minutes=5))

    with pytest.raises(DomainError, match="turno de captura vencio"):
        services.confirm_capture_batch(capture_batch=batch, actor=operator)

    batch.refresh_from_db()
    assert batch.status == CaptureBatch.Status.EXPIRED
    assert batch.confirmed_at is None
    assert AuditEvent.objects.filter(action="attendance.capture_batch.expired").count() == 1
