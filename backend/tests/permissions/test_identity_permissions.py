from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied

from apps.common.models import DomainError
from apps.identity.services import assign_role, protect_system_role
from apps.students.services import guardian_can_access_student
from tests.factories.academic import AcademicCycleFactory, InstitutionFactory, SectionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.students import GuardianFactory, StudentFactory, StudentGuardianRelationFactory


@pytest.mark.permissions
@pytest.mark.django_db
def test_default_deny_without_assignments():
    user = UserFactory()

    assert user.has_atomic_permission("student_view_basic") is False


@pytest.mark.permissions
@pytest.mark.django_db
def test_role_groups_permission():
    permission = PermissionFactory(codename="student_view_basic")
    role = RoleFactory(permissions=[permission])
    assignment = RoleAssignmentFactory(role=role)

    assert assignment.user.has_atomic_permission("student_view_basic") is True


@pytest.mark.permissions
@pytest.mark.django_db
def test_multiple_roles_union_permissions():
    read_permission = PermissionFactory(codename="student_view_basic")
    audit_permission = PermissionFactory(codename="audit_read")
    user = UserFactory()
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[read_permission]))
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[audit_permission]))

    assert user.has_atomic_permission("student_view_basic") is True
    assert user.has_atomic_permission("audit_read") is True


@pytest.mark.permissions
@pytest.mark.django_db
def test_scope_limits_permission():
    permission = PermissionFactory(codename="student_view_basic")
    institution = InstitutionFactory()
    assignment = RoleAssignmentFactory(
        role=RoleFactory(permissions=[permission]),
    )
    allowed_section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    denied_section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    ScopeGrantFactory(assignment=assignment, section=allowed_section)

    assert assignment.user.has_scoped_permission(
        "student_view_basic",
        scope={"section": allowed_section},
    )
    assert not assignment.user.has_scoped_permission(
        "student_view_basic",
        scope={"section": denied_section},
    )


@pytest.mark.permissions
@pytest.mark.django_db
def test_teacher_scope_depends_on_teaching_assignment():
    permission = PermissionFactory(codename="grade_capture")
    assignment = RoleAssignmentFactory(role=RoleFactory(permissions=[permission]))
    section = SectionFactory()
    teaching_assignment = section.teaching_assignments.create(
        academic_cycle=section.academic_cycle,
        section=section,
        subject=section.academic_cycle.institution.subjects.create(name="Math", code="MATH"),
        teacher=assignment.user.person,
    )
    ScopeGrantFactory(assignment=assignment, teaching_assignment=teaching_assignment)

    assert assignment.user.has_scoped_permission(
        "grade_capture",
        scope={"teaching_assignment": teaching_assignment},
    )


@pytest.mark.permissions
@pytest.mark.django_db
def test_guardian_scope_depends_on_active_relationship():
    guardian_person = GuardianFactory()
    guardian_user = UserFactory(person=guardian_person.person)
    student = StudentFactory()
    relation = StudentGuardianRelationFactory(guardian=guardian_person, student=student)

    assert guardian_can_access_student(user=guardian_user, student=student) is True

    relation.ends_at = relation.starts_at
    relation.save(update_fields=["ends_at", "updated_at"])

    assert (
        guardian_can_access_student(
            user=guardian_user,
            student=student,
            when=relation.starts_at + timedelta(days=1),
        )
        is False
    )


@pytest.mark.permissions
@pytest.mark.django_db
def test_role_union_keeps_scope_boundaries():
    permission = PermissionFactory(codename="student_view_basic")
    user = UserFactory()
    allowed_section = SectionFactory()
    denied_section = SectionFactory()
    second_allowed = SectionFactory()
    first_assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    second_assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    ScopeGrantFactory(assignment=first_assignment, section=allowed_section)
    ScopeGrantFactory(assignment=second_assignment, section=second_allowed)

    assert (
        user.has_scoped_permission("student_view_basic", scope={"section": denied_section}) is False
    )


@pytest.mark.permissions
@pytest.mark.django_db
def test_authorization_changes_apply_immediately():
    permission = PermissionFactory(codename="audit_read")
    role = RoleFactory(permissions=[permission])
    assignment = RoleAssignmentFactory(role=role)

    assert assignment.user.has_atomic_permission("audit_read") is True

    assignment.ends_at = assignment.starts_at
    assignment.save(update_fields=["ends_at", "updated_at"])

    assert (
        assignment.user.has_scoped_permission(
            "audit_read",
            when=assignment.ends_at + timedelta(microseconds=1),
        )
        is False
    )


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_user_cannot_self_assign_privileges():
    actor = UserFactory()
    role = RoleFactory(permissions=[PermissionFactory(codename="role_assign")])

    with pytest.raises(PermissionDenied):
        assign_role(actor=actor, user=actor, role=role)


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_system_roles_require_explicit_authorization_to_modify():
    role = RoleFactory(is_system=True)
    actor = UserFactory(is_superuser=False)

    with pytest.raises(DomainError):
        protect_system_role(actor=actor, role=role)
