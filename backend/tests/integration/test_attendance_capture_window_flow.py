"""
RF-JOR-001 and RF-AUT-005 end to end, against Postgres, with a real
enrolment: an operator's capture turn receives scans only inside the
jornada's operating window, and stops receiving them once its assigned time
elapses -- evaluated lazily on the next request (ADR-0009), never by a job.
"""

from datetime import date, datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.attendance import services
from apps.attendance.models import AttendanceEvent, CaptureBatch, DayStatus
from apps.audit.models import AuditEvent
from apps.enrolments.services import create_enrolment
from tests.factories.academic import AcademicCycleFactory, SectionFactory
from tests.factories.attendance import ControlPointFactory
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.integration, pytest.mark.postgres, pytest.mark.django_db]

WEDNESDAY = date(2026, 10, 7)
SUNDAY = date(2026, 10, 11)


def _at(day, hour, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


@pytest.fixture
def enrolled_jornada():
    cycle = AcademicCycleFactory(starts_on=date(2026, 1, 12), ends_on=date(2026, 11, 13))
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        opening_time=time(6, 0),
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(12, 30),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )
    return {
        "student": student,
        "shift": shift,
        "control_point": ControlPointFactory(campus=shift.campus),
    }


def _scan(jornada, operator, capture_batch, captured_at, client_event_id, movement_type):
    return services.record_scan_batch(
        items=[
            {
                "student": jornada["student"],
                "shift": jornada["shift"],
                "control_point": jornada["control_point"],
                "movement_type": movement_type,
                "captured_at": captured_at,
                "client_event_id": client_event_id,
                "capture_batch": capture_batch,
                "transmission": AttendanceEvent.Transmission.BATCH,
            }
        ],
        operator=operator,
    )[0]


def test_capture_turn_receives_only_in_window_scans(enrolled_jornada):
    """
    RF-JOR-001: within one capture turn, an in-window entry is registered
    while a Sunday scan and an after-closing exit are rejected without
    touching the derived status.
    """
    operator = UserFactory()
    batch = services.open_capture_batch(operator=operator)
    entry_type = AttendanceEvent.MovementType.ENTRY
    exit_type = AttendanceEvent.MovementType.EXIT

    entry = _scan(enrolled_jornada, operator, batch, _at(WEDNESDAY, 7, 5), "turn-entry", entry_type)
    sunday = _scan(enrolled_jornada, operator, batch, _at(SUNDAY, 7, 5), "turn-sunday", entry_type)
    after_close = _scan(
        enrolled_jornada, operator, batch, _at(WEDNESDAY, 23, 0), "turn-late-exit", exit_type
    )

    assert entry.outcome == "created"
    assert sunday.reason_code == "non_school_day"
    assert after_close.reason_code == "outside_operating_window"
    assert batch.events.count() == 1
    status = services.derive_day_status(
        student=enrolled_jornada["student"], shift=enrolled_jornada["shift"], event_date=WEDNESDAY
    )
    assert status.status == DayStatus.PRESENT
    assert status.entry_event.pk == entry.event.pk
    assert not AttendanceEvent.objects.filter(
        client_event_id__in=["turn-sunday", "turn-late-exit"]
    ).exists()


def test_capture_turn_stops_receiving_scans_once_its_assigned_time_elapses(enrolled_jornada):
    """
    RF-AUT-005: once the turn's assigned time elapses, the next scan closes
    and audits the turn and is rejected; recovery no longer offers it, and
    the movement captured before the expiry keeps its capture time.
    """
    operator = UserFactory()
    batch = services.open_capture_batch(operator=operator)
    entry_at = _at(WEDNESDAY, 7, 5)
    entry = _scan(
        enrolled_jornada,
        operator,
        batch,
        entry_at,
        "expiry-entry",
        AttendanceEvent.MovementType.ENTRY,
    )
    assert entry.outcome == "created"

    # The assigned time runs out; no job notices -- the next request does.
    CaptureBatch.objects.filter(pk=batch.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    batch.refresh_from_db()

    rejected = _scan(
        enrolled_jornada,
        operator,
        batch,
        _at(WEDNESDAY, 11, 0),
        "expiry-exit",
        AttendanceEvent.MovementType.EXIT,
    )

    assert rejected.reason_code == "capture_batch_expired"
    batch.refresh_from_db()
    assert batch.status == CaptureBatch.Status.EXPIRED
    assert AuditEvent.objects.filter(
        action="attendance.capture_batch.expired", resource_identifier=str(batch.public_id)
    ).exists()
    assert services.recover_open_capture_batch(operator=operator) is None
    kept = AttendanceEvent.objects.get(client_event_id="expiry-entry")
    assert kept.capture_batch_id == batch.pk
    assert kept.captured_at == entry_at
    assert not AttendanceEvent.objects.filter(client_event_id="expiry-exit").exists()
