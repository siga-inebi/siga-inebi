"""
RF-JOR-001 — contrato del endpoint de parametros de jornada.
RF-JOR-002 — contrato del endpoint de estado diario.
RF-JOR-003 — contrato del endpoint de resolucion de precedencia.
RF-JOR-004 — contrato del endpoint de cierre de jornada y de alertas.
RF-JOR-005 — contrato de alertas de inconsistencia generadas al registrar eventos.
RF-JOR-006 — recalculo ante cambios, disparado desde los mismos endpoints.
RF-JOR-008 — contrato del endpoint de presencia en tiempo real.
RF-JOR-009 — contrato del endpoint de porcentaje de asistencia del ciclo.
"""

from datetime import datetime, time, timedelta
from urllib.parse import urlencode

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.attendance import services
from apps.attendance.models import AttendanceAlert, AttendanceEvent
from apps.enrolments.services import create_enrolment
from tests.factories.academic import AcademicCycleFactory, SectionFactory, ShiftFactory
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


def test_close_jornada_requires_permission(auth_client):
    parameters = JornadaParametersFactory()

    response = auth_client.post(
        reverse("attendance-jornada-closures"),
        {"shift_id": str(parameters.shift.public_id), "event_date": str(parameters.effective_from)},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_close_jornada_creates_alert_for_permanence_without_closure(auth_client):
    """
    Escenario 1 (RF-JOR-004): GIVEN un estudiante con ingreso registrado y sin
    ningun egreso, WHEN se ejecuta el cierre de la jornada, THEN el sistema
    marca el dia con la condicion de permanencia sin cierre, AND genera una
    alerta dirigida al personal del punto de control y al coordinador de aula.
    """
    _grant(auth_client.user, CONFIGURE_PERMISSION)
    parameters = JornadaParametersFactory(closing_time=time(16, 0))
    section = SectionFactory(academic_cycle=parameters.academic_cycle, shift=parameters.shift)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=parameters.academic_cycle,
        grade=section.offering.grade,
        section=section,
    )
    _grant_student_scope(auth_client.user, student)
    AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(parameters.effective_from, time(7, 0))),
    )

    response = auth_client.post(
        reverse("attendance-jornada-closures"),
        {"shift_id": str(parameters.shift.public_id), "event_date": str(parameters.effective_from)},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["alerts"]) == 1
    alert = data["alerts"][0]
    assert alert["alert_type"] == "permanencia_sin_cierre"
    assert alert["student_id"] == str(student.public_id)
    assert set(alert["target_roles"]) == {"control_point", "section_coordinator"}

    alerts_response = auth_client.get(reverse("attendance-alert-list"))
    assert alerts_response.status_code == 200
    alert_ids = {item["public_id"] for item in alerts_response.json()["results"]}
    assert alert["public_id"] in alert_ids


def test_declared_exit_without_entry_creates_inconsistency_alert_visible_via_alerts_endpoint(
    auth_client,
):
    """
    Escenario 1 (RF-JOR-005): GIVEN un estudiante sin ingreso registrado en el
    dia, WHEN un docente lo incluye en el cierre declarado de su seccion,
    THEN el sistema conserva ambos hechos y genera una alerta de
    inconsistencia, AND identifica al docente y a la seccion como fuente de
    la declaracion.
    """
    _grant(auth_client.user, "attendance_declared_close")
    parameters = JornadaParametersFactory()
    section = SectionFactory(academic_cycle=parameters.academic_cycle, shift=parameters.shift)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=parameters.academic_cycle,
        grade=section.offering.grade,
        section=section,
    )
    _grant_student_scope(auth_client.user, student)

    response = auth_client.post(
        reverse("attendance-event-list"),
        _event_payload(
            student,
            parameters.shift,
            event_date=str(parameters.effective_from),
            origin=AttendanceEvent.Origin.DECLARED,
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    declared_event_id = response.json()["public_id"]

    alerts_response = auth_client.get(reverse("attendance-alert-list"))
    assert alerts_response.status_code == 200
    alerts = [
        item for item in alerts_response.json()["results"] if item["alert_type"] == "inconsistencia"
    ]
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["student_id"] == str(student.public_id)
    assert alert["section_id"] == str(section.public_id)
    assert alert["context"]["declared_event_id"] == declared_event_id
    assert alert["context"]["declared_by"] == auth_client.user.username


# --------------------------------------------------------------------------- #
# RF-JOR-006 — recalculo ante cambios
# --------------------------------------------------------------------------- #


def test_creating_a_past_dated_event_triggers_recalculation_reconciling_existing_alert(auth_client):
    _grant(auth_client.user, "attendance_scan")
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    cycle = AcademicCycleFactory(
        starts_on=yesterday - timedelta(days=30), ends_on=today + timedelta(days=30)
    )
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    _grant_student_scope(auth_client.user, student)
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
        captured_at=timezone.make_aware(datetime.combine(yesterday, time(7, 0))),
    )
    closure = services.close_jornada(shift=shift, event_date=yesterday)
    assert len(closure.alerts) == 1
    alert_id = closure.alerts[0].pk

    response = auth_client.post(
        reverse("attendance-event-list"),
        _event_payload(
            student,
            shift,
            event_date=str(yesterday),
            movement_type=AttendanceEvent.MovementType.EXIT,
            captured_at=timezone.make_aware(datetime.combine(yesterday, time(15, 0))).isoformat(),
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    alert = AttendanceAlert.objects.get(pk=alert_id)
    assert alert.is_active is False

    alerts_response = auth_client.get(reverse("attendance-alert-list"))
    assert alerts_response.status_code == 200
    alert_ids = {item["public_id"] for item in alerts_response.json()["results"]}
    assert str(alert.public_id) in alert_ids


def test_updating_jornada_parameters_does_not_change_earlier_days_derived_status(auth_client):
    _grant(auth_client.user, CONFIGURE_PERMISSION)
    today = timezone.localdate()
    cycle = AcademicCycleFactory(
        starts_on=today - timedelta(days=60), ends_on=today + timedelta(days=120)
    )
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    _grant_student_scope(auth_client.user, student)
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
    day_before = change_date - timedelta(days=1)
    AttendanceEventFactory(
        student=student,
        shift=shift,
        event_date=day_before,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(day_before, time(7, 15))),
    )

    before_response = auth_client.get(_day_status_url(student, shift, day_before))
    assert before_response.json()["status"] == "tarde"

    response = auth_client.post(
        reverse("attendance-jornada-parameters-list"),
        {
            "shift_id": str(shift.public_id),
            "academic_cycle_id": str(cycle.public_id),
            "entry_limit_time": "07:30:00",
            "tolerance_minutes": 15,
            "closing_time": "16:00:00",
            "duplicate_suppression_minutes": 5,
            "school_days": [1, 2, 3, 4, 5],
            "effective_from": str(change_date),
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    after_response = auth_client.get(_day_status_url(student, shift, day_before))
    assert after_response.json()["status"] == "tarde"


def _presence_url(shift, **params):
    query = urlencode({"shift_id": str(shift.public_id), **params})
    return f"{reverse('attendance-presence')}?{query}"


def test_presence_requires_authentication(client):
    shift = ShiftFactory()

    response = client.get(_presence_url(shift))

    assert response.status_code == 403


def test_presence_requires_student_scope(auth_client):
    shift = ShiftFactory()

    response = auth_client.get(_presence_url(shift, event_date=str(timezone.localdate())))

    assert response.status_code == 403


def test_presence_lists_only_students_with_entry_and_no_exit_within_scope(auth_client):
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    visible_student = StudentFactory()
    hidden_student = StudentFactory()
    create_enrolment(
        student=visible_student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
    )
    create_enrolment(
        student=hidden_student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
    )
    _grant_student_scope(auth_client.user, visible_student)
    JornadaParametersFactory(shift=shift, academic_cycle=cycle, effective_from=cycle.starts_on)
    for student in (visible_student, hidden_student):
        AttendanceEventFactory(
            student=student,
            shift=shift,
            event_date=cycle.starts_on,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            origin=AttendanceEvent.Origin.SCAN,
            captured_at=timezone.make_aware(datetime.combine(cycle.starts_on, time(7, 0))),
        )

    response = auth_client.get(_presence_url(shift, event_date=str(cycle.starts_on)))

    assert response.status_code == 200
    student_ids = {item["student_id"] for item in response.json()["results"]}
    assert student_ids == {str(visible_student.public_id)}


def test_presence_filters_by_section(auth_client):
    cycle = AcademicCycleFactory()
    section_a = SectionFactory(academic_cycle=cycle)
    section_b = SectionFactory(academic_cycle=cycle, shift=section_a.offering.shift)
    shift = section_a.offering.shift
    student_a = StudentFactory()
    student_b = StudentFactory()
    create_enrolment(
        student=student_a, academic_cycle=cycle, grade=section_a.offering.grade, section=section_a
    )
    create_enrolment(
        student=student_b, academic_cycle=cycle, grade=section_b.offering.grade, section=section_b
    )
    _grant_student_scope(auth_client.user, student_a)
    _grant_student_scope(auth_client.user, student_b)
    JornadaParametersFactory(shift=shift, academic_cycle=cycle, effective_from=cycle.starts_on)
    for student in (student_a, student_b):
        AttendanceEventFactory(
            student=student,
            shift=shift,
            event_date=cycle.starts_on,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            origin=AttendanceEvent.Origin.SCAN,
            captured_at=timezone.make_aware(datetime.combine(cycle.starts_on, time(7, 0))),
        )

    response = auth_client.get(
        _presence_url(shift, event_date=str(cycle.starts_on), section_id=str(section_a.public_id))
    )

    assert response.status_code == 200
    student_ids = {item["student_id"] for item in response.json()["results"]}
    assert student_ids == {str(student_a.public_id)}


def _percentage_url(student, shift, **params):
    query = urlencode(
        {"student_id": str(student.public_id), "shift_id": str(shift.public_id), **params}
    )
    return f"{reverse('attendance-percentage')}?{query}"


def test_percentage_requires_student_scope(auth_client):
    shift = ShiftFactory()
    student = StudentFactory()

    response = auth_client.get(_percentage_url(student, shift))

    assert response.status_code == 403


def test_percentage_returns_value_for_authorized_student(auth_client):
    day = timezone.localdate() - timedelta(days=1)
    cycle = AcademicCycleFactory(starts_on=day, ends_on=day + timedelta(days=200))
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
        effective_on=day,
    )
    _grant_student_scope(auth_client.user, student)
    JornadaParametersFactory(
        shift=shift, academic_cycle=cycle, effective_from=day, school_days=[1, 2, 3, 4, 5, 6, 7]
    )
    AttendanceEventFactory(
        student=student,
        shift=shift,
        event_date=day,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(day, time(7, 0))),
    )

    response = auth_client.get(_percentage_url(student, shift, as_of_date=str(day)))

    assert response.status_code == 200
    data = response.json()
    assert data["elapsed_school_days"] == 1
    assert data["present_days"] == 1
    assert data["percentage"] == 100.0
