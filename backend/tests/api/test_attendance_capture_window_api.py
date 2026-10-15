"""
HTTP contract of RF-JOR-001 (ventana operativa diaria): a rejected scan
reports a stable ``reason_code``.

Captures use fixed dates, so nothing here depends on when the suite runs.
"""

from datetime import date, datetime, time

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.attendance.models import AttendanceEvent
from apps.audit.models import AuditEvent
from apps.enrolments.services import create_enrolment
from tests.factories.academic import AcademicCycleFactory, SectionFactory, ShiftFactory
from tests.factories.attendance import (
    ControlPointFactory,
    JornadaParametersFactory,
    ManualRegistrationReasonFactory,
)
from tests.factories.identity import PermissionFactory, RoleAssignmentFactory, RoleFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

WEDNESDAY = date(2026, 10, 7)
SUNDAY = date(2026, 10, 11)


def _grant(user, *codenames):
    permissions = [PermissionFactory(codename=codename) for codename in codenames]
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=permissions))


def _at(day, hour, minute=0):
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
        closing_time=time(16, 0),
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )


def _post_scan(client, parameters, captured_at, client_event_id, **extra):
    # A scan by student code requires an active enrolment (RF-CRE-006).
    student = StudentFactory()
    section = SectionFactory(academic_cycle=parameters.academic_cycle)
    create_enrolment(
        student=student,
        academic_cycle=parameters.academic_cycle,
        grade=section.offering.grade,
        section=section,
    )
    item = {
        "client_event_id": client_event_id,
        "student_code": student.student_code,
        "shift_id": str(parameters.shift.public_id),
        "control_point_id": str(ControlPointFactory(campus=parameters.shift.campus).public_id),
        "movement_type": AttendanceEvent.MovementType.ENTRY,
        "captured_at": captured_at.isoformat(),
    }
    return client.post(
        reverse("attendance-scan"), {"items": [item], **extra}, content_type="application/json"
    )


@pytest.fixture
def operator_client(auth_client):
    _grant(auth_client.user, "attendance_scan", "attendance_record_entry")
    return auth_client


# --------------------------------------------------------------------------- #
# RF-JOR-001 — ventana operativa diaria
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "captured_at, reason_code",
    [
        (_at(SUNDAY, 8, 0), "non_school_day"),
        (_at(WEDNESDAY, 5, 30), "outside_operating_window"),
        (_at(WEDNESDAY, 23, 0), "outside_operating_window"),
    ],
    ids=["domingo", "antes-de-la-apertura", "despues-del-cierre"],
)
def test_scan_outside_the_operating_window_is_rejected_with_a_reason_code(
    operator_client, captured_at, reason_code
):
    """RF-JOR-001: Sunday, before opening and after closing are all rejected."""
    parameters = _parameters()

    response = _post_scan(operator_client, parameters, captured_at, "window-1")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["outcome"] == "rejected"
    assert item["reason_code"] == reason_code
    assert item["reason"]
    assert item["event"] is None
    assert not AttendanceEvent.objects.filter(client_event_id="window-1").exists()
    assert AuditEvent.objects.filter(
        action="attendance.event.rejected_outside_window", context__reason_code=reason_code
    ).exists()


def test_scan_inside_the_operating_window_is_created(operator_client):
    """RF-JOR-001: a school-day scan inside the window is registered."""
    parameters = _parameters()

    response = _post_scan(operator_client, parameters, _at(WEDNESDAY, 7, 0), "window-ok")

    item = response.json()[0]
    assert item["outcome"] == "created"
    assert item["reason_code"] == ""


def test_manual_registration_outside_the_window_is_a_bad_request(auth_client):
    """RF-JOR-001: the manual registration endpoint applies the same window."""
    _grant(auth_client.user, "attendance_record_manual", "attendance_record_entry")
    parameters = _parameters()

    response = auth_client.post(
        reverse("attendance-event-list"),
        {
            "student_id": str(StudentFactory().public_id),
            "shift_id": str(parameters.shift.public_id),
            "event_date": str(WEDNESDAY),
            "movement_type": AttendanceEvent.MovementType.ENTRY,
            "origin": "manual",
            "captured_at": _at(WEDNESDAY, 23, 0).isoformat(),
            "manual_reason_id": str(ManualRegistrationReasonFactory().public_id),
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "ventana operativa" in response.json()["error"]["detail"]
    assert not AttendanceEvent.objects.filter(shift=parameters.shift).exists()


def test_jornada_parameters_publish_the_opening_time(auth_client):
    """RF-JOR-001: the window's opening time is configurable through the API."""
    _grant(auth_client.user, "attendance_jornada_configure")
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.institution)

    response = auth_client.post(
        reverse("attendance-jornada-parameters-list"),
        {
            "shift_id": str(shift.public_id),
            "academic_cycle_id": str(cycle.public_id),
            "opening_time": "06:15",
            "entry_limit_time": "07:30",
            "tolerance_minutes": 10,
            "closing_time": "12:30",
            "duplicate_suppression_minutes": 5,
            "school_days": [1, 2, 3, 4, 5],
            "effective_from": str(cycle.starts_on),
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["opening_time"] == "06:15:00"
