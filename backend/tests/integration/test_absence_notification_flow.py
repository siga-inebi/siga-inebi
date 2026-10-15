"""
RF-JOR-007 — flujo completo: el personal ejecuta el cierre de jornada por la
API, el sistema determina la inasistencia y el encargado principal la
consulta en su listado de notificaciones.
"""

from datetime import time

import pytest
from django.test import Client
from django.urls import reverse

from apps.attendance import services
from apps.attendance.models import AbsenceNotification
from apps.audit.models import AuditEvent
from apps.enrolments.services import create_enrolment
from apps.students.services import create_student_guardian_relation
from tests.factories.academic import AcademicCycleFactory, SectionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.students import GuardianFactory, StudentFactory

pytestmark = [pytest.mark.integration, pytest.mark.postgres, pytest.mark.django_db]


def _client_with(user, codename):
    RoleAssignmentFactory(
        user=user, role=RoleFactory(permissions=[PermissionFactory(codename=codename)])
    )
    client = Client()
    client.force_login(user)
    return client


def test_jornada_closure_notifies_the_primary_guardian_of_an_absence():
    """
    RF-JOR-007: GIVEN un estudiante matriculado sin ingreso registrado y con
    encargado principal vigente, WHEN el personal ejecuta el cierre de la
    jornada (dos veces), THEN el encargado ve exactamente una notificacion de
    inasistencia de ese dia en su portal, AND su creacion queda auditada.
    """
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5, 6, 7],
        effective_from=cycle.starts_on,
    )
    guardian = GuardianFactory()
    create_student_guardian_relation(student=student, guardian=guardian, relationship_label="Madre")
    staff_client = _client_with(UserFactory(), "attendance_jornada_configure")
    guardian_client = _client_with(
        UserFactory(person=guardian.person), "attendance_absence_notification_view"
    )

    for _ in range(2):
        closure = staff_client.post(
            reverse("attendance-jornada-closures"),
            {"shift_id": str(shift.public_id), "event_date": str(cycle.starts_on)},
            content_type="application/json",
        )
        assert closure.status_code == 200

    response = guardian_client.get(reverse("attendance-absence-notification-list"))

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["student_id"] == str(student.public_id)
    assert results[0]["absence_date"] == str(cycle.starts_on)
    notification = AbsenceNotification.objects.get()
    assert AuditEvent.objects.filter(
        action="attendance.absence_notification.created",
        resource_identifier=str(notification.public_id),
    ).exists()
