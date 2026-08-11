"""
RF-JOR-001 — contrato del endpoint de parametros de jornada.
RF-JOR-002 — contrato del endpoint de estado diario.
RF-JOR-003 — contrato del endpoint de resolucion de precedencia.
"""

from datetime import datetime, time
from urllib.parse import urlencode

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.attendance.models import AttendanceEvent
from tests.factories.academic import AcademicCycleFactory, ShiftFactory
from tests.factories.attendance import AttendanceEventFactory, JornadaParametersFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

CONFIGURE_PERMISSION = "attendance_jornada_configure"
STUDENT_VIEW_PERMISSION = "student_view_basic"


def _grant(user, codename):
    permission = PermissionFactory(codename=codename)
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


def _grant_student_scope(user, student, codename=STUDENT_VIEW_PERMISSION):
    permission = PermissionFactory(codename=codename)
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    return ScopeGrantFactory(assignment=assignment, student=student)


def _payload(shift, cycle):
    return {
        "shift_id": str(shift.public_id),
        "academic_cycle_id": str(cycle.public_id),
        "entry_limit_time": "07:00:00",
        "tolerance_minutes": 10,
        "closing_time": "13:00:00",
        "duplicate_suppression_minutes": 5,
        "school_days": [1, 2, 3, 4, 5],
        "effective_from": str(cycle.starts_on),
    }


def test_create_jornada_parameters_requires_permission(auth_client):
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.institution)

    response = auth_client.post(
        reverse("attendance-jornada-parameters-list"),
        _payload(shift, cycle),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_jornada_parameters_with_permission(auth_client):
    _grant(auth_client.user, CONFIGURE_PERMISSION)
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.institution)

    response = auth_client.post(
        reverse("attendance-jornada-parameters-list"),
        _payload(shift, cycle),
        content_type="application/json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["entry_limit_time"] == "07:00:00"
    assert data["shift_id"] == str(shift.public_id)


def test_create_jornada_parameters_with_unknown_shift_is_rejected(auth_client):
    _grant(auth_client.user, CONFIGURE_PERMISSION)
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.institution)
    payload = _payload(shift, cycle)
    payload["shift_id"] = "00000000-0000-0000-0000-000000000000"

    response = auth_client.post(
        reverse("attendance-jornada-parameters-list"),
        payload,
        content_type="application/json",
    )

    assert response.status_code == 400


def test_list_jornada_parameters_requires_permission(auth_client):
    response = auth_client.get(reverse("attendance-jornada-parameters-list"))

    assert response.status_code == 403


def test_unauthenticated_request_is_rejected(client):
    response = client.get(reverse("attendance-jornada-parameters-list"))

    assert response.status_code == 403


def _event_payload(student, shift, **overrides):
    payload = {
        "student_id": str(student.public_id),
        "shift_id": str(shift.public_id),
        "event_date": str(timezone.localdate()),
        "movement_type": AttendanceEvent.MovementType.EXIT,
        "origin": AttendanceEvent.Origin.SCAN,
        "captured_at": timezone.now().isoformat(),
    }
    payload.update(overrides)
    return payload


def test_create_attendance_event_requires_matching_origin_permission(auth_client):
    student = StudentFactory()
    shift = ShiftFactory()

    response = auth_client.post(
        reverse("attendance-event-list"),
        _event_payload(student, shift),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_attendance_event_with_permission(auth_client):
    _grant(auth_client.user, "attendance_scan")
    student = StudentFactory()
    shift = ShiftFactory()

    response = auth_client.post(
        reverse("attendance-event-list"),
        _event_payload(student, shift),
        content_type="application/json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["origin"] == AttendanceEvent.Origin.SCAN
    assert data["student_id"] == str(student.public_id)


def test_list_attendance_events_only_shows_authorized_students(auth_client):
    visible_student = StudentFactory()
    hidden_student = StudentFactory()
    shift = ShiftFactory()

    AttendanceEventFactory(student=visible_student, shift=shift)
    AttendanceEventFactory(student=hidden_student, shift=shift)
    _grant_student_scope(auth_client.user, visible_student)

    response = auth_client.get(reverse("attendance-event-list"))

    assert response.status_code == 200
    student_ids = {item["student_id"] for item in response.json()["results"]}
    assert student_ids == {str(visible_student.public_id)}


def _day_status_url(student, shift, event_date):
    query = urlencode(
        {
            "student_id": str(student.public_id),
            "shift_id": str(shift.public_id),
            "event_date": str(event_date),
        }
    )
    return f"{reverse('attendance-day-status')}?{query}"


def test_day_status_returns_present_for_early_entry(auth_client):
    parameters = JornadaParametersFactory(entry_limit_time=time(7, 30))
    student = StudentFactory()
    _grant_student_scope(auth_client.user, student)
    AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(parameters.effective_from, time(7, 0))),
    )

    response = auth_client.get(
        _day_status_url(student, parameters.shift, parameters.effective_from)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "presente"


def test_day_status_requires_student_scope(auth_client):
    parameters = JornadaParametersFactory()
    student = StudentFactory()

    response = auth_client.get(
        _day_status_url(student, parameters.shift, parameters.effective_from)
    )

    assert response.status_code == 403


def test_day_status_without_configured_parameters_is_a_bad_request(auth_client):
    shift = ShiftFactory()
    student = StudentFactory()
    _grant_student_scope(auth_client.user, student)

    response = auth_client.get(_day_status_url(student, shift, timezone.localdate()))

    assert response.status_code == 400


def _resolution_url(student, shift, event_date, movement_type):
    query = urlencode(
        {
            "student_id": str(student.public_id),
            "shift_id": str(shift.public_id),
            "event_date": str(event_date),
            "movement_type": movement_type,
        }
    )
    return f"{reverse('attendance-event-resolution')}?{query}"


def test_resolution_returns_scan_event_over_declared(auth_client):
    shift = ShiftFactory()
    student = StudentFactory()
    event_date = timezone.localdate()
    _grant_student_scope(auth_client.user, student)
    scan_event = AttendanceEventFactory(
        student=student,
        shift=shift,
        event_date=event_date,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.now(),
    )
    AttendanceEventFactory(
        student=student,
        shift=shift,
        event_date=event_date,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.DECLARED,
        captured_at=timezone.now(),
    )

    response = auth_client.get(
        _resolution_url(student, shift, event_date, AttendanceEvent.MovementType.EXIT)
    )

    assert response.status_code == 200
    assert response.json()["public_id"] == str(scan_event.public_id)


def test_resolution_requires_student_scope(auth_client):
    shift = ShiftFactory()
    student = StudentFactory()

    response = auth_client.get(
        _resolution_url(student, shift, timezone.localdate(), AttendanceEvent.MovementType.EXIT)
    )

    assert response.status_code == 403


def test_resolution_returns_404_when_no_event_matches(auth_client):
    shift = ShiftFactory()
    student = StudentFactory()
    _grant_student_scope(auth_client.user, student)

    response = auth_client.get(
        _resolution_url(student, shift, timezone.localdate(), AttendanceEvent.MovementType.EXIT)
    )

    assert response.status_code == 404


def test_resolution_with_malformed_query_is_a_bad_request(auth_client):
    response = auth_client.get(f"{reverse('attendance-event-resolution')}?movement_type=exit")

    assert response.status_code == 400
