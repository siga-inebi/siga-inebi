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
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import TeachingAssignment
from apps.attendance import services
from apps.attendance.models import AttendanceAlert, AttendanceEvent, CaptureBatch, StudentCredential
from apps.audit.models import AuditEvent
from apps.enrolments.models import Enrolment
from apps.enrolments.services import create_enrolment
from tests.factories.academic import (
    AcademicCycleFactory,
    SectionFactory,
    ShiftFactory,
    SubjectFactory,
)
from tests.factories.attendance import (
    AttendanceEventFactory,
    CaptureBatchFactory,
    ControlPointFactory,
    JornadaParametersFactory,
    ManualRegistrationReasonFactory,
)
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
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
    _grant(auth_client.user, "attendance_record_exit")
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
    _grant(auth_client.user, "attendance_record_exit")
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
# RF-ASI-011 — cierre declarado por seccion
# --------------------------------------------------------------------------- #


def _grant_declared_closure_permission(user):
    _grant(user, "attendance_declared_close")
    _grant(user, "attendance_record_exit")


def _section_closure_preview_url(section, event_date):
    query = urlencode({"section_id": str(section.public_id), "event_date": str(event_date)})
    return f"{reverse('attendance-section-closure-preview')}?{query}"


def test_section_closure_preview_requires_permission(auth_client):
    parameters = JornadaParametersFactory()
    section = SectionFactory(academic_cycle=parameters.academic_cycle, shift=parameters.shift)

    response = auth_client.get(_section_closure_preview_url(section, parameters.effective_from))

    assert response.status_code == 403


def test_section_closure_requires_permission(auth_client):
    parameters = JornadaParametersFactory()
    section = SectionFactory(academic_cycle=parameters.academic_cycle, shift=parameters.shift)

    response = auth_client.post(
        reverse("attendance-section-closure"),
        {"section_id": str(section.public_id), "event_date": str(parameters.effective_from)},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_section_closure_preview_shows_omitted_students_before_confirming(auth_client):
    """
    Escenario 1 (RF-ASI-011): GIVEN una seccion con un estudiante sin
    ingreso registrado, WHEN un usuario autorizado previsualiza el cierre
    declarado, THEN el resumen lo muestra omitido con el motivo, AND no se
    registra ningun movimiento.
    """
    _grant_declared_closure_permission(auth_client.user)
    parameters = JornadaParametersFactory()
    section = SectionFactory(academic_cycle=parameters.academic_cycle, shift=parameters.shift)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=parameters.academic_cycle,
        grade=section.offering.grade,
        section=section,
    )

    response = auth_client.get(_section_closure_preview_url(section, parameters.effective_from))

    assert response.status_code == 200
    data = response.json()
    assert data["included"] == []
    assert len(data["omitted"]) == 1
    assert data["omitted"][0]["student_id"] == str(student.public_id)
    assert not AttendanceEvent.objects.filter(student=student).exists()


def test_section_closure_confirms_declared_exit_for_eligible_students(auth_client):
    """
    Escenario 2 (RF-ASI-011): GIVEN una seccion con un estudiante que tiene
    ingreso y sin salida, WHEN un usuario autorizado confirma el cierre
    declarado, THEN el sistema registra su salida declarada, AND el resumen
    lo muestra incluido, no omitido.
    """
    _grant_declared_closure_permission(auth_client.user)
    parameters = JornadaParametersFactory()
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
        captured_at=timezone.make_aware(datetime.combine(parameters.effective_from, time(7, 0))),
    )

    response = auth_client.post(
        reverse("attendance-section-closure"),
        {
            "section_id": str(section.public_id),
            "event_date": str(parameters.effective_from),
            "confirmed": True,
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["included"] == [{"student_id": str(student.public_id)}]
    assert data["omitted"] == []
    event = AttendanceEvent.objects.get(
        student=student, movement_type=AttendanceEvent.MovementType.EXIT
    )
    assert event.origin == AttendanceEvent.Origin.DECLARED


def test_section_closure_omits_a_student_who_already_has_an_exit(auth_client):
    _grant_declared_closure_permission(auth_client.user)
    parameters = JornadaParametersFactory()
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
        captured_at=timezone.make_aware(datetime.combine(parameters.effective_from, time(7, 0))),
    )
    AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.EXIT,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(parameters.effective_from, time(12, 0))),
    )

    response = auth_client.post(
        reverse("attendance-section-closure"),
        {
            "section_id": str(section.public_id),
            "event_date": str(parameters.effective_from),
            "confirmed": True,
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["included"] == []
    assert len(data["omitted"]) == 1
    assert data["omitted"][0]["student_id"] == str(student.public_id)
    assert (
        AttendanceEvent.objects.filter(
            student=student, movement_type=AttendanceEvent.MovementType.EXIT
        ).count()
        == 1
    )


# --------------------------------------------------------------------------- #
# RF-ASI-013 — trazabilidad y confirmacion del cierre por cobertura
# --------------------------------------------------------------------------- #


def _assign_teacher(*, parameters, section, teacher):
    TeachingAssignment.objects.create(
        academic_cycle=parameters.academic_cycle,
        section=section,
        subject=SubjectFactory(institution=parameters.academic_cycle.institution),
        teacher=teacher.person,
        starts_on=parameters.academic_cycle.starts_on,
    )


def test_section_closure_requires_confirmation_from_a_covering_teacher(auth_client):
    """
    Escenario 1 (RF-ASI-013): GIVEN una seccion cuyo docente asignado no es
    quien declara el cierre, WHEN ese docente de cobertura lo declara sin
    confirmar, THEN la API no registra nada, AND responde que se necesita
    confirmacion, mostrando la seccion, el grado y los estudiantes
    involucrados.
    """
    _grant_declared_closure_permission(auth_client.user)
    parameters = JornadaParametersFactory()
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
        captured_at=timezone.make_aware(datetime.combine(parameters.effective_from, time(7, 0))),
    )

    response = auth_client.post(
        reverse("attendance-section-closure"),
        {"section_id": str(section.public_id), "event_date": str(parameters.effective_from)},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["confirmation_required"] is True
    assert data["is_covering"] is True
    assert data["grade_name"] == section.offering.grade.name
    assert data["included"] == [{"student_id": str(student.public_id)}]
    assert not AttendanceEvent.objects.filter(
        student=student, movement_type=AttendanceEvent.MovementType.EXIT
    ).exists()


def test_section_closure_does_not_require_confirmation_from_the_assigned_teacher(auth_client):
    _grant_declared_closure_permission(auth_client.user)
    parameters = JornadaParametersFactory()
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
        captured_at=timezone.make_aware(datetime.combine(parameters.effective_from, time(7, 0))),
    )
    _assign_teacher(parameters=parameters, section=section, teacher=auth_client.user)

    response = auth_client.post(
        reverse("attendance-section-closure"),
        {"section_id": str(section.public_id), "event_date": str(parameters.effective_from)},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["confirmation_required"] is False
    assert data["is_covering"] is False
    assert AttendanceEvent.objects.filter(
        student=student, movement_type=AttendanceEvent.MovementType.EXIT
    ).exists()


def test_coverage_ratio_requires_permission(auth_client):
    response = auth_client.get(reverse("attendance-section-closure-coverage-ratio"))

    assert response.status_code == 403


def test_coverage_ratio_reflects_confirmed_closures(auth_client):
    """
    Escenario 3 (RF-ASI-013): GIVEN cierres ya confirmados por docentes
    asignados y de cobertura, WHEN un usuario autorizado consulta la
    proporcion, THEN la API la calcula de lo ya registrado.
    """
    _grant(auth_client.user, CONFIGURE_PERMISSION)
    parameters = JornadaParametersFactory()
    section = SectionFactory(academic_cycle=parameters.academic_cycle, shift=parameters.shift)
    assigned_teacher = UserFactory()
    _assign_teacher(parameters=parameters, section=section, teacher=assigned_teacher)
    covering_teacher = UserFactory()
    services.close_section(
        section=section, event_date=parameters.effective_from, actor=assigned_teacher
    )
    services.close_section(
        section=section,
        event_date=parameters.effective_from,
        actor=covering_teacher,
        confirmed=True,
    )

    response = auth_client.get(
        f"{reverse('attendance-section-closure-coverage-ratio')}?section_id={section.public_id}"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_closures"] == 2
    assert data["covering_closures"] == 1
    assert data["coverage_ratio"] == 0.5


# --------------------------------------------------------------------------- #
# RF-JOR-006 — recalculo ante cambios
# --------------------------------------------------------------------------- #


def test_creating_a_past_dated_event_triggers_recalculation_reconciling_existing_alert(auth_client):
    _grant(auth_client.user, "attendance_scan")
    _grant(auth_client.user, "attendance_record_exit")
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
    _grant(auth_client.user, "attendance_record_entry")
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


def test_scan_endpoint_rejects_a_movement_type_the_control_point_does_not_allow(auth_client):
    """
    Escenario 1 (RF-ASI-005): GIVEN un punto de control configurado solo
    para egreso, WHEN un operador intenta registrar un ingreso desde ese
    punto, THEN el sistema rechaza la operacion indicando que el punto no
    admite ingresos.
    """
    _grant(auth_client.user, "attendance_scan")
    _grant(auth_client.user, "attendance_record_entry")
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    _enrol(student, parameters.academic_cycle)
    control_point = ControlPointFactory(campus=parameters.shift.campus, allows_entry=False)
    item = _scan_item(student, parameters.shift, control_point, "unsupported-1", timezone.now())

    response = auth_client.post(
        reverse("attendance-scan"), {"items": [item]}, content_type="application/json"
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["outcome"] == "rejected"
    assert "no admite ingresos" in body[0]["reason"]


def test_scan_endpoint_confirmation_shows_only_photo_name_grade_and_section(auth_client):
    """
    RF-ASI-003: la confirmacion trae exactamente foto, nombre completo, grado
    y seccion -- nada de salud, calificaciones, contacto ni domicilio.
    """
    _grant(auth_client.user, "attendance_scan")
    _grant(auth_client.user, "attendance_record_entry")
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    section = SectionFactory(academic_cycle=parameters.academic_cycle, shift=parameters.shift)
    create_enrolment(
        student=student,
        academic_cycle=parameters.academic_cycle,
        grade=section.offering.grade,
        section=section,
    )
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    item = _scan_item(student, parameters.shift, control_point, "confirmation-1", timezone.now())

    response = auth_client.post(
        reverse("attendance-scan"), {"items": [item]}, content_type="application/json"
    )

    assert response.status_code == 200
    confirmation = response.json()[0]["confirmation"]
    assert set(confirmation.keys()) == {
        "student_id",
        "full_name",
        "grade_name",
        "section_name",
        "photo_url",
    }
    assert confirmation["student_id"] == str(student.public_id)
    assert confirmation["full_name"] == f"{student.person.first_name} {student.person.last_name}"
    assert confirmation["grade_name"] == section.offering.grade.name
    assert confirmation["section_name"] == section.name


def test_scan_endpoint_rejects_duplicate_and_reports_existing_captured_at(auth_client):
    _grant(auth_client.user, "attendance_scan")
    _grant(auth_client.user, "attendance_record_entry")
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
    _grant(auth_client.user, "attendance_record_entry")
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
    _grant(auth_client.user, "attendance_record_entry")
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


def _queries_for_scan_batch(auth_client, *, items):
    with CaptureQueriesContext(connection) as captured:
        response = auth_client.post(
            reverse("attendance-scan"), {"items": items}, content_type="application/json"
        )
    assert response.status_code == 200
    return len(captured.captured_queries)


def test_scan_batch_does_not_requery_the_same_shift_control_point_and_permission_per_item(
    auth_client,
):
    """
    RF-ASI-014: a batch overwhelmingly repeats the same shift, control point
    and movement-type permission across its items (one operator, one control
    point, one jornada). Comparing two batches of the *same* size N -- one
    where every item shares those three keys, one where every item has its
    own -- isolates exactly the caching effect: if repeating a key never saved
    a query, both batches would cost the same regardless of what else the
    request does. It doesn't: the shared-key batch costs strictly less.
    """
    _grant(auth_client.user, "attendance_scan")
    _grant(auth_client.user, "attendance_record_entry")
    _grant(auth_client.user, "attendance_record_exit")
    now = timezone.now()

    shared_parameters = JornadaParametersFactory()
    shared_control_point = ControlPointFactory(campus=shared_parameters.shift.campus)
    shared_students = [StudentFactory() for _ in range(4)]
    for student in shared_students:
        _enrol(student, shared_parameters.academic_cycle)
    shared_key_items = [
        _scan_item(student, shared_parameters.shift, shared_control_point, f"shared-{i}", now)
        for i, student in enumerate(shared_students)
    ]

    unique_key_items = []
    for i in range(4):
        parameters = JornadaParametersFactory()
        control_point = ControlPointFactory(campus=parameters.shift.campus)
        student = StudentFactory()
        _enrol(student, parameters.academic_cycle)
        unique_key_items.append(
            _scan_item(
                student,
                parameters.shift,
                control_point,
                f"unique-{i}",
                now,
                movement_type=(
                    AttendanceEvent.MovementType.ENTRY
                    if i % 2 == 0
                    else AttendanceEvent.MovementType.EXIT
                ),
            )
        )

    shared_key_queries = _queries_for_scan_batch(auth_client, items=shared_key_items)
    unique_key_queries = _queries_for_scan_batch(auth_client, items=unique_key_items)

    assert shared_key_queries < unique_key_queries


def test_scan_endpoint_reports_scanned_captured_at_distinct_from_server_created_at(auth_client):
    """
    RF-ASI-008: la hora de captura que llega en el item del escaneo se
    conserva tal cual en la respuesta; la hora de registro (``created_at``)
    es la del servidor al momento de procesar la solicitud, no la del
    dispositivo que escaneo.
    """
    _grant(auth_client.user, "attendance_scan")
    _grant(auth_client.user, "attendance_record_entry")
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
# RF-ASI-009 — lote de captura recuperable
# --------------------------------------------------------------------------- #


def test_open_capture_batch_endpoint_requires_authentication(client):
    response = client.post(reverse("attendance-capture-batch-open"))

    assert response.status_code == 403


def test_open_capture_batch_endpoint_requires_permission(auth_client):
    response = auth_client.post(reverse("attendance-capture-batch-open"))

    assert response.status_code == 403


def test_open_capture_batch_endpoint_is_idempotent(auth_client):
    _grant(auth_client.user, "attendance_scan")

    first = auth_client.post(reverse("attendance-capture-batch-open"))
    second = auth_client.post(reverse("attendance-capture-batch-open"))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["public_id"] == second.json()["public_id"]


def test_current_capture_batch_endpoint_returns_none_when_nothing_is_open(auth_client):
    _grant(auth_client.user, "attendance_scan")

    response = auth_client.get(reverse("attendance-capture-batch-current"))

    assert response.status_code == 200
    body = response.json()
    assert body["capture_batch"] is None
    assert body["events"] == []


def test_current_capture_batch_endpoint_recovers_pending_batch_with_original_capture_times(
    auth_client,
):
    """
    Escenario 1 (RF-ASI-009): GIVEN un operador con un lote abierto que
    contiene doce movimientos escaneados, WHEN la sesion se pierde y el
    usuario se vuelve a autenticar, THEN el sistema presenta el lote
    pendiente con los doce elementos, AND cada elemento conserva su hora de
    captura original.
    """
    _grant(auth_client.user, "attendance_scan")
    _grant(auth_client.user, "attendance_record_entry")
    parameters = JornadaParametersFactory()
    control_point = ControlPointFactory(campus=parameters.shift.campus)

    open_response = auth_client.post(reverse("attendance-capture-batch-open"))
    capture_batch_id = open_response.json()["public_id"]

    captured_times = []
    for index in range(12):
        student = StudentFactory()
        _enrol(student, parameters.academic_cycle)
        captured_at = timezone.make_aware(
            datetime.combine(parameters.effective_from, time(7, index))
        )
        captured_times.append(captured_at)
        item = _scan_item(
            student, parameters.shift, control_point, f"batch-item-{index}", captured_at
        )
        response = auth_client.post(
            reverse("attendance-scan"),
            {"capture_batch_id": capture_batch_id, "items": [item]},
            content_type="application/json",
        )
        assert response.json()[0]["outcome"] == "created"

    response = auth_client.get(reverse("attendance-capture-batch-current"))

    assert response.status_code == 200
    body = response.json()
    assert body["capture_batch"]["public_id"] == capture_batch_id
    assert len(body["events"]) == 12
    recovered_times = {datetime.fromisoformat(event["captured_at"]) for event in body["events"]}
    assert recovered_times == set(captured_times)


def test_confirm_capture_batch_endpoint_closes_it(auth_client):
    _grant(auth_client.user, "attendance_scan")
    batch = CaptureBatchFactory(operator=auth_client.user)

    response = auth_client.post(reverse("attendance-capture-batch-confirm", args=[batch.public_id]))

    assert response.status_code == 200
    assert response.json()["status"] == CaptureBatch.Status.CONFIRMED


def test_confirm_capture_batch_endpoint_rejects_a_batch_belonging_to_another_operator(auth_client):
    _grant(auth_client.user, "attendance_scan")
    someone_elses_batch = CaptureBatchFactory()

    response = auth_client.post(
        reverse("attendance-capture-batch-confirm", args=[someone_elses_batch.public_id])
    )

    assert response.status_code == 400


def test_scan_endpoint_links_the_created_event_to_the_capture_batch(auth_client):
    _grant(auth_client.user, "attendance_scan")
    _grant(auth_client.user, "attendance_record_entry")
    parameters = JornadaParametersFactory()
    student = StudentFactory()
    _enrol(student, parameters.academic_cycle)
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    batch = CaptureBatchFactory(operator=auth_client.user)
    item = _scan_item(student, parameters.shift, control_point, "linked-item-1", timezone.now())

    response = auth_client.post(
        reverse("attendance-scan"),
        {"capture_batch_id": str(batch.public_id), "items": [item]},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()[0]["outcome"] == "created"
    assert batch.events.count() == 1


# --------------------------------------------------------------------------- #
# RF-ASI-012 — registro manual autorizado
# --------------------------------------------------------------------------- #


def test_manual_registration_reasons_list_requires_authentication(client):
    response = client.get(reverse("attendance-manual-registration-reason-list"))

    assert response.status_code == 403


def test_manual_registration_reasons_list_returns_catalogue(auth_client):
    reason = ManualRegistrationReasonFactory()

    response = auth_client.get(reverse("attendance-manual-registration-reason-list"))

    assert response.status_code == 200
    codes = {item["code"] for item in response.json()["results"]}
    assert reason.code in codes


def test_create_manual_attendance_event_requires_reason(auth_client):
    _grant(auth_client.user, "attendance_record_manual")
    _grant(auth_client.user, "attendance_record_entry")
    student = StudentFactory()
    shift = ShiftFactory()

    response = auth_client.post(
        reverse("attendance-event-list"),
        _event_payload(
            student, shift, movement_type=AttendanceEvent.MovementType.ENTRY, origin="manual"
        ),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_manual_attendance_event_stores_reason_and_operator(auth_client):
    """
    Escenario 1 (RF-ASI-012): GIVEN un estudiante que olvido su credencial,
    WHEN un usuario con permiso elevado registra su ingreso indicando el
    motivo, THEN el sistema crea un evento con origen manual, el motivo y la
    identidad del autorizador.
    """
    _grant(auth_client.user, "attendance_record_manual")
    _grant(auth_client.user, "attendance_record_entry")
    student = StudentFactory()
    shift = ShiftFactory()
    reason = ManualRegistrationReasonFactory(name="Olvido su credencial")

    response = auth_client.post(
        reverse("attendance-event-list"),
        _event_payload(
            student,
            shift,
            movement_type=AttendanceEvent.MovementType.ENTRY,
            origin="manual",
            manual_reason_id=str(reason.public_id),
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["origin"] == "manual"
    assert data["manual_reason_id"] == str(reason.public_id)
    assert data["operator_id"] == auth_client.user.pk


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
# RF-CRE-002 — contrato del endpoint de contenido imprimible de la credencial
# --------------------------------------------------------------------------- #


def _print_content_url(student):
    return f"{reverse('attendance-credential-print-content')}?student_id={student.public_id}"


def test_credential_print_content_requires_authentication(client):
    student = StudentFactory()

    response = client.get(_print_content_url(student))

    assert response.status_code == 403


def test_credential_print_content_requires_permission_and_student_scope(auth_client):
    student = StudentFactory()
    _enrol(student)
    services.issue_credential(student=student)

    response = auth_client.get(_print_content_url(student))

    assert response.status_code == 403


def test_credential_print_content_returns_exactly_the_allowed_fields(auth_client):
    """
    RF-CRE-002: la respuesta trae nombre, foto, grado, seccion, ciclo e
    institucion -- nada de salud, calificaciones, contacto ni domicilio.
    """
    student = StudentFactory()
    section = _enrol(student)
    services.issue_credential(student=student)
    _grant_student_scope(auth_client.user, student, codename=CREDENTIAL_ISSUE_PERMISSION)

    response = auth_client.get(_print_content_url(student))

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "student_id",
        "full_name",
        "grade_name",
        "section_name",
        "academic_cycle_name",
        "institution_name",
        "photo_url",
    }
    assert body["student_id"] == str(student.public_id)
    assert body["grade_name"] == section.offering.grade.name
    assert body["section_name"] == section.name


def test_credential_print_content_without_an_active_credential_is_a_bad_request(auth_client):
    student = StudentFactory()
    _enrol(student)
    _grant_student_scope(auth_client.user, student, codename=CREDENTIAL_ISSUE_PERMISSION)

    response = auth_client.get(_print_content_url(student))

    assert response.status_code == 400


# --------------------------------------------------------------------------- #
# RF-CRE-003 — contrato de revocacion de credencial
# --------------------------------------------------------------------------- #


def _revoke_credential(client, student, reason="Extravío"):
    return client.post(
        reverse("attendance-credential-revoke"),
        {"student_id": str(student.public_id), "reason": reason},
        content_type="application/json",
    )


def test_revoke_credential_requires_authentication(client):
    assert _revoke_credential(client, StudentFactory()).status_code == 403


def test_revoke_credential_requires_permission_and_student_scope(auth_client):
    student = StudentFactory()
    _enrol(student)
    services.issue_credential(student=student)

    assert _revoke_credential(auth_client, student).status_code == 403


def test_revoke_credential_records_reason_and_revoker(auth_client):
    student = StudentFactory()
    _enrol(student)
    services.issue_credential(student=student)
    _grant_student_scope(auth_client.user, student, codename=CREDENTIAL_ISSUE_PERMISSION)

    response = _revoke_credential(auth_client, student, reason="Extravío reportado por tutor")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == StudentCredential.Status.REVOKED
    assert body["revocation_reason"] == "Extravío reportado por tutor"
    assert body["revoked_by_id"] == auth_client.user.pk
    assert "opaque_identifier" not in body


def test_revoke_credential_requires_a_reason(auth_client):
    student = StudentFactory()
    _enrol(student)
    services.issue_credential(student=student)
    _grant_student_scope(auth_client.user, student, codename=CREDENTIAL_ISSUE_PERMISSION)

    response = _revoke_credential(auth_client, student, reason="")

    assert response.status_code == 400


def test_revoke_credential_without_an_active_one_is_a_bad_request(auth_client):
    student = StudentFactory()
    _enrol(student)
    _grant_student_scope(auth_client.user, student, codename=CREDENTIAL_ISSUE_PERMISSION)

    assert _revoke_credential(auth_client, student).status_code == 400


# --------------------------------------------------------------------------- #
# RF-CRE-005 — persistencia de los movimientos ante revocacion
# --------------------------------------------------------------------------- #


def test_revoking_a_credential_does_not_alter_the_students_day_status(auth_client):
    """
    Escenario 1 (RF-CRE-005): GIVEN un estudiante con un movimiento de
    asistencia ya registrado, WHEN se revoca su credencial, THEN el estado
    diario consultado por API sigue siendo exactamente el mismo.
    """
    parameters = JornadaParametersFactory(entry_limit_time=time(7, 30))
    student = StudentFactory()
    _enrol(student)
    _grant_student_scope(auth_client.user, student)
    _grant_student_scope(auth_client.user, student, codename=CREDENTIAL_ISSUE_PERMISSION)
    services.issue_credential(student=student)
    AttendanceEventFactory(
        student=student,
        shift=parameters.shift,
        event_date=parameters.effective_from,
        movement_type=AttendanceEvent.MovementType.ENTRY,
        origin=AttendanceEvent.Origin.SCAN,
        captured_at=timezone.make_aware(datetime.combine(parameters.effective_from, time(7, 0))),
    )
    url = _day_status_url(student, parameters.shift, parameters.effective_from)
    before = auth_client.get(url).json()

    assert _revoke_credential(auth_client, student).status_code == 200

    after = auth_client.get(url).json()
    assert after == before


# --------------------------------------------------------------------------- #
# RF-CRE-004 — reposicion sin perdida de historial
# --------------------------------------------------------------------------- #


def test_reissuing_after_revocation_via_the_api_generates_a_new_identifier(auth_client):
    """
    Escenario 1 (RF-CRE-004): GIVEN un estudiante cuya credencial fue
    revocada, WHEN un usuario autorizado emite la reposicion, THEN el
    sistema genera un identificador opaco distinto del anterior, AND el
    historial de credenciales del estudiante conserva la credencial
    revocada.
    """
    student = StudentFactory()
    _enrol(student)
    _grant_student_scope(auth_client.user, student, codename=CREDENTIAL_ISSUE_PERMISSION)
    first = services.issue_credential(student=student)

    revoke_response = _revoke_credential(auth_client, student, reason="Extravio")
    assert revoke_response.status_code == 200

    reissue_response = auth_client.post(
        reverse("attendance-credential-issue"),
        {"student_id": str(student.public_id)},
        content_type="application/json",
    )

    assert reissue_response.status_code == 201
    body = reissue_response.json()
    assert body["opaque_identifier"] != first.opaque_identifier
    assert body["status"] == StudentCredential.Status.ACTIVE
    assert StudentCredential.objects.filter(student=student).count() == 2


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
    _grant(auth_client.user, "attendance_record_entry")
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
    _grant(auth_client.user, "attendance_record_entry")
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
    _grant(auth_client.user, "attendance_record_entry")
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
