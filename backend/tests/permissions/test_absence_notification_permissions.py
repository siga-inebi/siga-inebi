"""
RF-JOR-007 — el alcance del encargado sobre las notificaciones de
inasistencia deriva de su relacion vigente: al terminarla deja de verlas,
incluidas las emitidas mientras estuvo vigente (openspec
autorizacion-alcance, "Corte total al terminar la asociacion").
"""

import pytest
from django.urls import reverse

from apps.attendance import services
from apps.audit.models import AuditEvent
from apps.common.exceptions import AuthorizationError
from apps.students.services import (
    change_primary_student_guardian_relation,
    create_student_guardian_relation,
    end_student_guardian_relation,
)
from tests.factories.attendance import JornadaParametersFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.students import GuardianFactory, StudentFactory

pytestmark = [pytest.mark.permissions, pytest.mark.security, pytest.mark.django_db]

VIEW_PERMISSION = "attendance_absence_notification_view"


def _guardian_user():
    guardian = GuardianFactory()
    user = UserFactory(person=guardian.person)
    RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[PermissionFactory(codename=VIEW_PERMISSION)]),
        identity_scope=False,
    )
    return guardian, user


def test_ended_relationship_cuts_access_to_past_absence_notifications(client):
    """
    RF-JOR-007: GIVEN un encargado notificado de una inasistencia de su
    estudiante, WHEN su asociacion termina, THEN deja de ver esa
    notificacion, AND sigue viendo las de su otro estudiante vigente.
    """
    parameters = JornadaParametersFactory()
    guardian, user = _guardian_user()
    ended_ward = StudentFactory()
    current_ward = StudentFactory()
    ended_relation = create_student_guardian_relation(
        student=ended_ward, guardian=guardian, relationship_label="Madre"
    )
    create_student_guardian_relation(
        student=current_ward, guardian=guardian, relationship_label="Madre"
    )
    for student in (ended_ward, current_ward):
        services.notify_absence(
            student=student, shift=parameters.shift, absence_date=parameters.effective_from
        )

    replacement = create_student_guardian_relation(
        student=ended_ward, guardian=GuardianFactory(), relationship_label="Padre"
    )
    change_primary_student_guardian_relation(relation=replacement)
    ended_relation.refresh_from_db()
    end_student_guardian_relation(relation=ended_relation)

    visible = services.list_my_absence_notifications(user=user)
    assert [notification.student for notification in visible] == [current_ward]

    client.force_login(user)
    response = client.get(reverse("attendance-absence-notification-list"))
    assert response.status_code == 200
    assert [item["student_id"] for item in response.json()["results"]] == [
        str(current_ward.public_id)
    ]


def test_guardian_with_no_current_relationship_is_denied_and_audited():
    """RF-JOR-007: sin ninguna relacion vigente no hay alcance; la denegacion se audita."""
    _guardian, user = _guardian_user()

    with pytest.raises(AuthorizationError):
        services.list_my_absence_notifications(user=user)

    assert AuditEvent.objects.filter(
        action="identity.authorization.denied", context__permission=VIEW_PERMISSION
    ).exists()
