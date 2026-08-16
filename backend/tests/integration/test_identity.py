import pytest

from apps.academics.services import create_teaching_assignment
from apps.identity.scopes import scope_matches
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.integration, pytest.mark.postgres, pytest.mark.django_db]


def test_write_scope_denies_mutations_when_cycle_transitions_to_closed():
    """
    RF-ALC-005 (Integration): Cross-domain validation that active teaching assignments
    and administrative grants automatically lose write capabilities once the cycle closes.
    """
    cycle = AcademicCycleFactory(status="active")
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=cycle.institution)
    teacher = TeacherFactory()
    teacher_user = UserFactory(person=teacher.person)

    write_permission = PermissionFactory(codename="grade_write")
    correct_permission = PermissionFactory(codename="grade_correct")
    read_permission = PermissionFactory(codename="student_view_basic")

    RoleAssignmentFactory(
        user=teacher_user,
        role=RoleFactory(permissions=[write_permission, correct_permission, read_permission]),
    )
    assignment = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
    )

    # 1. En ciclo activo, el docente tiene alcance de escritura
    assert (
        scope_matches(
            user=teacher_user,
            codename="grade_write",
            scope={"teaching_assignment": assignment},
        )
        is True
    )
    assert (
        scope_matches(
            user=teacher_user,
            codename="grade_write",
            scope={"section": section, "subject": subject},
        )
        is True
    )

    # 2. Transición del ciclo a cerrado
    cycle.status = cycle.CycleStatus.CLOSED
    cycle.save(update_fields=["status", "updated_at"])
    assignment.refresh_from_db()
    section.refresh_from_db()

    # 3. Tras el cierre, las operaciones de escritura quedan inmediatamente denegadas
    assert (
        scope_matches(
            user=teacher_user,
            codename="grade_write",
            scope={"teaching_assignment": assignment},
        )
        is False
    )
    assert (
        scope_matches(
            user=teacher_user,
            codename="grade_correct",
            scope={"teaching_assignment": assignment},
        )
        is False
    )

    # 4. Las operaciones de lectura administrativa sobre la estructura cerrada se preservan
    admin_user = UserFactory()
    admin_role = RoleFactory(permissions=[write_permission, read_permission])
    admin_assignment = RoleAssignmentFactory(user=admin_user, role=admin_role)
    ScopeGrantFactory(assignment=admin_assignment, section=section)

    assert (
        scope_matches(
            user=admin_user,
            codename="student_view_basic",
            scope={"section": section},
        )
        is True
    )
    assert (
        scope_matches(
            user=admin_user,
            codename="grade_write",
            scope={"section": section},
        )
        is False
    )
