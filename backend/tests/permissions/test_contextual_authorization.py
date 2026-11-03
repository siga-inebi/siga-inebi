import pytest

from apps.academics.models import TeachingAssignment
from tests.factories.academic import (
    AcademicCycleFactory,
    InstitutionFactory,
    SectionFactory,
    SubjectFactory,
)
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.students import StudentFactory


@pytest.mark.permissions
@pytest.mark.django_db
def test_contextual_permission_without_scope_is_denied():
    permission = PermissionFactory(codename="student_view_basic")
    user = UserFactory()
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))

    assert user.has_atomic_permission("student_view_basic") is True
    assert user.has_scoped_permission("student_view_basic") is False
    assert (
        user.has_scoped_permission("student_view_basic", scope={"student": StudentFactory()})
        is False
    )


@pytest.mark.permissions
@pytest.mark.django_db
def test_institution_scope_matches_students_enrolled_in_its_sections():
    permission = PermissionFactory(codename="student_view_basic")
    institution = InstitutionFactory()
    user = UserFactory()
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    ScopeGrantFactory(assignment=assignment, institution=institution)

    assert user.has_scoped_permission("student_view_basic", scope={"section": section}) is True


@pytest.mark.permissions
@pytest.mark.django_db
def test_role_scopes_are_union_of_active_grants():
    permission = PermissionFactory(codename="student_view_basic")
    user = UserFactory()
    first_assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    second_assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    first_student = StudentFactory()
    second_student = StudentFactory()
    ScopeGrantFactory(assignment=first_assignment, student=first_student)
    ScopeGrantFactory(assignment=second_assignment, student=second_student)

    assert user.has_scoped_permission("student_view_basic", scope={"student": first_student})
    assert user.has_scoped_permission("student_view_basic", scope={"student": second_student})


@pytest.mark.permissions
@pytest.mark.django_db
def test_teacher_without_assignment_is_denied_grade_write_scope():
    """
    RF-CAL-006, Escenario 1: Subárea ajena.
    GIVEN un docente con el permiso grade_write pero sin asignación docente
    WHEN se evalúa su alcance sobre una sección y subárea que no le pertenecen
    THEN el sistema deniega el alcance
    """
    permission = PermissionFactory(codename="grade_write")
    user = UserFactory()
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=cycle.institution)

    assert (
        user.has_scoped_permission("grade_write", scope={"section": section, "subject": subject})
        is False
    )


@pytest.mark.permissions
@pytest.mark.django_db
def test_teacher_with_matching_assignment_has_grade_write_scope():
    """
    Mirror of Escenario 1: a docente WITH a matching teaching assignment over
    the section and subject is granted scope, unlike the ajena case above.
    """
    permission = PermissionFactory(codename="grade_write")
    user = UserFactory()
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=cycle.institution)
    TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=user.person,
        starts_on=cycle.starts_on,
    )

    assert (
        user.has_scoped_permission("grade_write", scope={"section": section, "subject": subject})
        is True
    )
