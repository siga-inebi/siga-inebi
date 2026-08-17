import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.services import create_teaching_assignment
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.api, pytest.mark.postgres, pytest.mark.django_db]


def test_api_rejection_for_write_operation_on_closed_cycle():
    """
    Validar que el API rechace mutaciones cuando el actor
    intenta operar sobre una asignación de un ciclo cerrado.
    """
    cycle = AcademicCycleFactory(status="active")
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=cycle.institution)
    teacher = TeacherFactory()
    teacher_user = UserFactory(person=teacher.person)

    write_permission = PermissionFactory(codename="grade_write")
    RoleAssignmentFactory(
        user=teacher_user,
        role=RoleFactory(permissions=[write_permission]),
    )
    assignment = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
    )

    client = APIClient()
    client.force_authenticate(user=teacher_user)

    # El ciclo se cierra
    cycle.status = cycle.CycleStatus.CLOSED
    cycle.save(update_fields=["status", "updated_at"])
    assignment.refresh_from_db()

    # Intento de realizar escritura sobre el ciclo cerrado a través de endpoints
    assert (
        teacher_user.has_scoped_permission(
            "grade_write",
            scope={"teaching_assignment": assignment},
        )
        is False
    )

    # Endpoint protegido por permisos responde denegado (403 Forbidden)
    response = client.post(
        reverse("teaching-assignment-reassign", args=[assignment.public_id]),
        {"teacher_id": str(TeacherFactory().public_id), "ends_on": "2026-06-30"},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
