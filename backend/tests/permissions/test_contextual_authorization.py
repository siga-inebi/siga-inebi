import pytest

from tests.factories.academic import AcademicCycleFactory, InstitutionFactory, SectionFactory
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
