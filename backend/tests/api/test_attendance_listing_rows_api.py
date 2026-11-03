"""
#631 (AS6) — las filas de los listados de asistencia traen el nombre del estudiante.

La interfaz del personal dejó de descargar el padrón completo de estudiantes
para pintar el nombre de cada fila (docs/ux-ui.md 1.1 y 1.3). Los listados de
movimientos, alertas, presencia y el turno de captura agregan
``student: {public_id, student_code, full_name}`` sin quitar ``student_id`` y sin
que el número de consultas crezca con las filas.
"""

from datetime import datetime, time

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.attendance.models import AttendanceEvent
from apps.enrolments.services import create_enrolment
from tests.factories.academic import AcademicCycleFactory, SectionFactory, ShiftFactory
from tests.factories.attendance import (
    AttendanceAlertFactory,
    AttendanceEventFactory,
    CaptureBatchFactory,
    JornadaParametersFactory,
)
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

STUDENT_VIEW = "student_view_basic"


def _grant(user, codename, *students):
    permission = PermissionFactory(codename=codename)
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    for student in students:
        ScopeGrantFactory(assignment=assignment, student=student)


def _named_student(code="EST-7001"):
    return StudentFactory(
        student_code=code, person=PersonFactory(first_name="Ana", last_name="Pérez")
    )


def test_event_rows_carry_the_student_name(auth_client):
    student = _named_student()
    _grant(auth_client.user, STUDENT_VIEW, student)
    AttendanceEventFactory(student=student)

    response = auth_client.get(reverse("attendance-event-list"))

    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["student_id"] == str(student.public_id)
    assert row["student"] == {
        "public_id": str(student.public_id),
        "student_code": "EST-7001",
        "full_name": "Ana Pérez",
    }


def test_event_rows_do_not_grow_queries_with_rows(auth_client):
    students = [StudentFactory() for _ in range(5)]
    _grant(auth_client.user, STUDENT_VIEW, *students)
    shift = ShiftFactory()
    url = reverse("attendance-event-list")
    AttendanceEventFactory(student=students[0], shift=shift)

    with CaptureQueriesContext(connection) as one_row:
        assert auth_client.get(url).status_code == 200

    for student in students[1:]:
        AttendanceEventFactory(student=student, shift=ShiftFactory())
    with CaptureQueriesContext(connection) as five_rows:
        response = auth_client.get(url)

    assert response.json()["count"] == 5
    assert len(five_rows) == len(one_row)


def test_alert_rows_carry_the_student_name(auth_client):
    student = _named_student("EST-7002")
    _grant(auth_client.user, STUDENT_VIEW, student)
    AttendanceAlertFactory(student=student)

    response = auth_client.get(reverse("attendance-alert-list"))

    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["student"]["full_name"] == "Ana Pérez"
    assert row["student"]["student_code"] == "EST-7002"


@pytest.mark.usefixtures("operating_window_clock")
def test_presence_rows_carry_the_student_name(auth_client):
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = _named_student("EST-7003")
    create_enrolment(
        student=student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
    )
    _grant(auth_client.user, STUDENT_VIEW, student)
    JornadaParametersFactory(shift=shift, academic_cycle=cycle, effective_from=cycle.starts_on)
    AttendanceEventFactory(
        student=student,
        shift=shift,
        event_date=cycle.starts_on,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        captured_at=timezone.make_aware(datetime.combine(cycle.starts_on, time(7, 0))),
    )

    response = auth_client.get(
        reverse("attendance-presence"),
        {"shift_id": str(shift.public_id), "event_date": str(cycle.starts_on)},
    )

    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["student"]["full_name"] == "Ana Pérez"


def test_current_capture_batch_events_carry_the_student_name(auth_client):
    _grant(auth_client.user, "attendance_scan")
    student = _named_student("EST-7004")
    batch = CaptureBatchFactory(operator=auth_client.user)
    AttendanceEventFactory(student=student, capture_batch=batch)

    response = auth_client.get(reverse("attendance-capture-batch-current"))

    assert response.status_code == 200
    events = response.json()["events"]
    assert [event["student"]["full_name"] for event in events] == ["Ana Pérez"]
