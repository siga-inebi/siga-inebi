"""
RF-JOR-001 — contrato del endpoint de parametros de jornada.
RF-JOR-002 — contrato del endpoint de estado diario.
RF-JOR-003 — contrato del endpoint de resolucion de precedencia.
RF-JOR-004 — contrato del endpoint de cierre de jornada y de alertas.
RF-JOR-005 — contrato de alertas de inconsistencia generadas al registrar eventos.
RF-JOR-006 — recalculo ante cambios, disparado desde los mismos endpoints.
RF-JOR-008 — contrato del endpoint de presencia en tiempo real.
RF-JOR-009 — contrato del endpoint de porcentaje de asistencia del ciclo.
RF-JOR-011 — el endpoint de porcentaje siempre incluye la advertencia
reglamentaria.
RF-ASI-001/002/004/010 — contrato del endpoint de captura por escaneo y del
catalogo de puntos de control.
RF-CRE-001 — contrato del endpoint de emision de credencial.
RF-CRE-006 — contrato del endpoint de resolucion de identificador.
"""

from datetime import datetime, time, timedelta
from urllib.parse import urlencode

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.attendance import services
from apps.attendance.models import AttendanceAlert, AttendanceEvent, StudentCredential
from apps.audit.models import AuditEvent
from apps.enrolments.models import Enrolment
from apps.enrolments.services import create_enrolment
from tests.factories.academic import AcademicCycleFactory, SectionFactory, ShiftFactory
from tests.factories.attendance import (
    AttendanceEventFactory,
    ControlPointFactory,
    JornadaParametersFactory,
)
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


def _scan_item(student, shift, control_point, client_event_id, captured_at, **overrides):
    item = {
        "client_event_id": client_event_id,
        "student_code": student.student_code,
        "shift_id": str(shift.public_id),
        "control_point_id": str(control_point.public_id),
        "movement_type": AttendanceEvent.MovementType.ENTRY,
        "captured_at": captured_at.isoformat(),
    }
    item.update(overrides)
    return item


def test_scan_endpoint_requires_authentication(client):
    response = client.post(
        reverse("attendance-scan"), {"items": []}, content_type="application/json"
    )

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


def test_scan_endpoint_requires_attendance_scan_permission(auth_client):
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    item = _scan_item(student, parameters.shift, control_point, "perm-1", timezone.now())

    response = auth_client.post(
        reverse("attendance-scan"), {"items": [item]}, content_type="application/json"
    )

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
    assert data["regulatory_notice"]


def test_scan_endpoint_creates_event_with_permission(auth_client):
    _grant(auth_client.user, "attendance_scan")
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    _enrol(student, parameters.academic_cycle)
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    item = _scan_item(student, parameters.shift, control_point, "created-1", timezone.now())

    response = auth_client.post(
        reverse("attendance-scan"), {"items": [item]}, content_type="application/json"
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["outcome"] == "created"
    assert body[0]["event"]["origin"] == AttendanceEvent.Origin.SCAN
    assert body[0]["event"]["control_point_id"] == str(control_point.public_id)


def test_scan_endpoint_rejects_duplicate_and_reports_existing_captured_at(auth_client):
    _grant(auth_client.user, "attendance_scan")
    parameters = JornadaParametersFactory(duplicate_suppression_minutes=10)
    student = StudentFactory()
    _enrol(student, parameters.academic_cycle)
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    captured_at = timezone.make_aware(datetime.combine(parameters.effective_from, time(7, 0)))

    auth_client.post(
        reverse("attendance-scan"),
        {"items": [_scan_item(student, parameters.shift, control_point, "dup-1", captured_at)]},
        content_type="application/json",
    )
    response = auth_client.post(
        reverse("attendance-scan"),
        {
            "items": [
                _scan_item(
                    student,
                    parameters.shift,
                    control_point,
                    "dup-2",
                    captured_at + timedelta(minutes=2),
                )
            ]
        },
        content_type="application/json",
    )

    body = response.json()
    assert body[0]["outcome"] == "duplicate_suppressed"
    assert body[0]["duplicate_of"]["captured_at"] is not None


def test_scan_endpoint_resend_with_same_client_event_id_is_idempotent(auth_client):
    _grant(auth_client.user, "attendance_scan")
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    _enrol(student, parameters.academic_cycle)
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    item = _scan_item(student, parameters.shift, control_point, "idempotent-1", timezone.now())

    auth_client.post(reverse("attendance-scan"), {"items": [item]}, content_type="application/json")
    response = auth_client.post(
        reverse("attendance-scan"), {"items": [item]}, content_type="application/json"
    )

    assert response.status_code == 200
    assert response.json()[0]["outcome"] == "already_processed"
    assert AttendanceEvent.objects.filter(client_event_id="idempotent-1").count() == 1


def test_scan_batch_endpoint_reports_mixed_outcomes_per_item(auth_client):
    _grant(auth_client.user, "attendance_scan")
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    _enrol(student, parameters.academic_cycle)
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    now = timezone.now()
    items = [
        _scan_item(student, parameters.shift, control_point, "mix-1", now),
        {
            "client_event_id": "mix-2",
            "student_code": "does-not-exist",
            "shift_id": str(parameters.shift.public_id),
            "control_point_id": str(control_point.public_id),
            "movement_type": AttendanceEvent.MovementType.ENTRY,
            "captured_at": now.isoformat(),
        },
    ]

    response = auth_client.post(
        reverse("attendance-scan"), {"items": items}, content_type="application/json"
    )

    assert response.status_code == 200
    outcomes = [entry["outcome"] for entry in response.json()]
    assert outcomes == ["created", "rejected"]


def test_scan_endpoint_reports_scanned_captured_at_distinct_from_server_created_at(auth_client):
    """
    RF-ASI-008: la hora de captura que llega en el item del escaneo se
    conserva tal cual en la respuesta; la hora de registro (``created_at``)
    es la del servidor al momento de procesar la solicitud, no la del
    dispositivo que escaneo.
    """
    _grant(auth_client.user, "attendance_scan")
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    _enrol(student, parameters.academic_cycle)
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    scanned_at = timezone.make_aware(datetime.combine(parameters.effective_from, time(12, 20)))

    before_request = timezone.now()
    response = auth_client.post(
        reverse("attendance-scan"),
        {"items": [_scan_item(student, parameters.shift, control_point, "clock-1", scanned_at)]},
        content_type="application/json",
    )
    after_request = timezone.now()

    assert response.status_code == 200
    event = response.json()[0]["event"]
    assert event["captured_at"] == scanned_at.isoformat()
    reported_created_at = datetime.fromisoformat(event["created_at"])
    assert before_request <= reported_created_at <= after_request


def test_control_points_list_requires_authentication(client):
    response = client.get(reverse("attendance-control-point-list"))

    assert response.status_code == 403


def test_control_points_list_returns_catalogue(auth_client):
    control_point = ControlPointFactory()

    response = auth_client.get(reverse("attendance-control-point-list"))

    assert response.status_code == 200
    codes = {item["code"] for item in response.json()["results"]}
    assert control_point.code in codes


# --------------------------------------------------------------------------- #
# RF-CRE-001 — contrato del endpoint de emision de credencial
# --------------------------------------------------------------------------- #

CREDENTIAL_ISSUE_PERMISSION = "attendance_credential_issue"


def _enrol(student, cycle=None):
    cycle = cycle or AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    create_enrolment(
        student=student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
    )
    return section


def test_issue_credential_requires_permission_and_student_scope(auth_client):
    student = StudentFactory()
    _enrol(student)

    response = auth_client.post(
        reverse("attendance-credential-issue"),
        {"student_id": str(student.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 403
    assert not StudentCredential.objects.filter(student=student).exists()


def test_issue_credential_returns_the_opaque_identifier(auth_client):
    student = StudentFactory()
    _enrol(student)
    _grant_student_scope(auth_client.user, student, codename=CREDENTIAL_ISSUE_PERMISSION)

    response = auth_client.post(
        reverse("attendance-credential-issue"),
        {"student_id": str(student.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["student_id"] == str(student.public_id)
    assert body["status"] == StudentCredential.Status.ACTIVE
    assert body["opaque_identifier"]
    assert student.student_code not in body["opaque_identifier"]


def test_issue_credential_for_a_student_without_active_enrolment_is_a_bad_request(auth_client):
    student = StudentFactory()
    _grant_student_scope(auth_client.user, student, codename=CREDENTIAL_ISSUE_PERMISSION)

    response = auth_client.post(
        reverse("attendance-credential-issue"),
        {"student_id": str(student.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert not StudentCredential.objects.filter(student=student).exists()


def test_issue_credential_with_unknown_student_is_a_bad_request(auth_client):
    student = StudentFactory()
    _grant_student_scope(auth_client.user, student, codename=CREDENTIAL_ISSUE_PERMISSION)

    response = auth_client.post(
        reverse("attendance-credential-issue"),
        {"student_id": "00000000-0000-0000-0000-000000000000"},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_issue_credential_requires_authentication(client):
    response = client.post(
        reverse("attendance-credential-issue"),
        {"student_id": "00000000-0000-0000-0000-000000000000"},
        content_type="application/json",
    )

    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------- #
# RF-CRE-006 — contrato del endpoint de resolucion de identificador
# --------------------------------------------------------------------------- #

CREDENTIAL_RESOLVE_PERMISSION = "attendance_credential_resolve"


def _resolve_credential(client, identifier):
    return client.post(
        reverse("attendance-credential-resolve"),
        {"opaque_identifier": identifier},
        content_type="application/json",
    )


def _issued_credential(student=None, cycle=None):
    student = student or StudentFactory()
    _enrol(student, cycle)
    return student, services.issue_credential(student=student)


def test_resolve_credential_requires_permission(auth_client):
    _student, credential = _issued_credential()

    response = _resolve_credential(auth_client, credential.opaque_identifier)

    assert response.status_code == 403


def test_resolve_unknown_identifier_returns_400_without_any_student_data(auth_client):
    """Escenario 1 (RF-CRE-006) sobre el contrato HTTP."""
    student, credential = _issued_credential()
    _grant(auth_client.user, CREDENTIAL_RESOLVE_PERMISSION)

    response = _resolve_credential(auth_client, "no-such-token")

    assert response.status_code == 400
    body = response.content.decode()
    assert "no es reconocida" in body
    assert student.student_code not in body
    assert str(student.public_id) not in body
    assert credential.opaque_identifier not in body


def test_resolve_credential_of_withdrawn_student_returns_400(auth_client):
    """Escenario 2 (RF-CRE-006) sobre el contrato HTTP."""
    student, credential = _issued_credential()
    _grant(auth_client.user, CREDENTIAL_RESOLVE_PERMISSION)
    enrolment = student.enrolments.get()
    enrolment.status = Enrolment.EnrolmentStatus.WITHDRAWN
    enrolment.save(update_fields=["status"])

    response = _resolve_credential(auth_client, credential.opaque_identifier)

    assert response.status_code == 400
    body = response.content.decode()
    assert "no tiene inscripcion activa" in body
    assert student.student_code not in body


def test_resolve_credential_returns_the_bearer_and_audits_the_read(auth_client):
    student, credential = _issued_credential()
    _grant(auth_client.user, CREDENTIAL_RESOLVE_PERMISSION)

    response = _resolve_credential(auth_client, credential.opaque_identifier)

    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == str(student.public_id)
    assert body["student_code"] == student.student_code
    assert body["full_name"] == str(student.person)
    assert body["credential_status"] == StudentCredential.Status.ACTIVE
    # The token is not echoed back: the caller already has it.
    assert credential.opaque_identifier not in response.content.decode()
    assert AuditEvent.objects.filter(action="attendance.credential.resolved").exists()


def test_resolve_credential_requires_authentication(client):
    response = _resolve_credential(client, "any-token")

    assert response.status_code in (401, 403)


def test_scan_with_a_credential_identifier_creates_the_event(auth_client):
    _grant(auth_client.user, "attendance_scan")
    parameters = JornadaParametersFactory()
    student, credential = _issued_credential(cycle=parameters.academic_cycle)
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    item = _scan_item(student, parameters.shift, control_point, "cred-1", timezone.now())
    item.pop("student_code")
    item["credential_identifier"] = credential.opaque_identifier

    response = auth_client.post(
        reverse("attendance-scan"), {"items": [item]}, content_type="application/json"
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["outcome"] == "created"
    assert body[0]["event"]["student_id"] == str(student.public_id)


def test_scan_with_an_unknown_credential_rejects_only_that_item(auth_client):
    _grant(auth_client.user, "attendance_scan")
    parameters = JornadaParametersFactory()
    student, credential = _issued_credential(cycle=parameters.academic_cycle)
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    good = _scan_item(student, parameters.shift, control_point, "cred-ok", timezone.now())
    good.pop("student_code")
    good["credential_identifier"] = credential.opaque_identifier
    bad = _scan_item(student, parameters.shift, control_point, "cred-bad", timezone.now())
    bad.pop("student_code")
    bad["credential_identifier"] = "unknown-token"

    response = auth_client.post(
        reverse("attendance-scan"),
        {"batch_id": "mixed", "items": [bad, good]},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["outcome"] == "rejected"
    assert "no es reconocida" in body[0]["reason"]
    assert body[1]["outcome"] == "created"


def test_scan_item_must_identify_the_subject_exactly_one_way(auth_client):
    _grant(auth_client.user, "attendance_scan")
    parameters = JornadaParametersFactory()
    student, credential = _issued_credential(cycle=parameters.academic_cycle)
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    both = _scan_item(student, parameters.shift, control_point, "cred-both", timezone.now())
    both["credential_identifier"] = credential.opaque_identifier

    response = auth_client.post(
        reverse("attendance-scan"), {"items": [both]}, content_type="application/json"
    )

    assert response.status_code == 400

    neither = _scan_item(student, parameters.shift, control_point, "cred-none", timezone.now())
    neither.pop("student_code")

    response = auth_client.post(
        reverse("attendance-scan"), {"items": [neither]}, content_type="application/json"
    )

    assert response.status_code == 400


def test_scan_by_student_code_of_a_withdrawn_student_is_rejected(auth_client):
    """
    El elemento del estudiante retirado se rechaza y no aborta el resto del
    lote: el companero que si esta inscrito registra su movimiento.
    """
    _grant(auth_client.user, "attendance_scan")
    parameters = JornadaParametersFactory()
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    withdrawn = StudentFactory()
    _enrol(withdrawn, parameters.academic_cycle)
    enrolled = StudentFactory()
    _enrol(enrolled, parameters.academic_cycle)

    enrolment = withdrawn.enrolments.get()
    enrolment.status = Enrolment.EnrolmentStatus.WITHDRAWN
    enrolment.save(update_fields=["status"])

    now = timezone.now()
    response = auth_client.post(
        reverse("attendance-scan"),
        {
            "batch_id": "withdrawn-mix",
            "items": [
                _scan_item(withdrawn, parameters.shift, control_point, "wd-1", now),
                _scan_item(enrolled, parameters.shift, control_point, "wd-2", now),
            ],
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["outcome"] == "rejected"
    assert "no tiene inscripcion activa" in body[0]["reason"]
    assert body[1]["outcome"] == "created"
    assert not AttendanceEvent.objects.filter(student=withdrawn).exists()
