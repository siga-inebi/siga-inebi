import pytest

from apps.identity.scopes import authorized_student_queryset
from apps.students.models import Student
from apps.students.services import create_student_guardian_relation
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.students import GuardianFactory, StudentFactory


@pytest.mark.permissions
@pytest.mark.django_db
def test_guardian_scope_contains_only_current_related_students():
    permission = PermissionFactory(codename="student_view_basic")
    guardian = GuardianFactory()
    user = UserFactory(person=guardian.person)
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    related_student = StudentFactory()
    unrelated_student = StudentFactory()
    create_student_guardian_relation(
        student=related_student,
        guardian=guardian,
        relationship_label="Madre",
    )

    visible_ids = set(
        authorized_student_queryset(user=user, codename="student_view_basic").values_list(
            "pk", flat=True
        )
    )

    assert visible_ids == {related_student.pk}
    assert unrelated_student.pk not in visible_ids


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_ended_guardian_relationship_revokes_scope_immediately():
    permission = PermissionFactory(codename="student_view_basic")
    guardian = GuardianFactory()
    user = UserFactory(person=guardian.person)
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    relation = create_student_guardian_relation(
        student=student,
        guardian=guardian,
        relationship_label="Madre",
    )
    relation.ends_at = relation.starts_at
    relation.save(update_fields=["ends_at", "updated_at"])

    assert not user.has_scoped_permission("student_view_basic", scope={"student": student})


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_withdrawn_ward_loses_scope_without_hiding_other_active_wards():
    permission = PermissionFactory(codename="student_view_basic")
    guardian = GuardianFactory()
    user = UserFactory(person=guardian.person)
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    withdrawn = StudentFactory(status=Student.StudentStatus.ACTIVE)
    active = StudentFactory(status=Student.StudentStatus.ACTIVE)
    for student in (withdrawn, active):
        create_student_guardian_relation(
            student=student,
            guardian=guardian,
            relationship_label="Madre",
        )
    withdrawn.status = Student.StudentStatus.WITHDRAWN
    withdrawn.save(update_fields=["status", "updated_at"])

    visible = authorized_student_queryset(user=user, codename="student_view_basic")

    assert list(visible) == [active]
    assert user.is_active


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_withdrawn_student_account_keeps_account_but_loses_permissions():
    permission = PermissionFactory(codename="student_view_basic")
    student = StudentFactory(status=Student.StudentStatus.ACTIVE)
    user = UserFactory(person=student.person)
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    assert user.has_atomic_permission("student_view_basic")

    student.status = Student.StudentStatus.WITHDRAWN
    student.save(update_fields=["status", "updated_at"])

    assert not user.has_atomic_permission("student_view_basic")
    user.refresh_from_db()
    assert user.is_active
    assert user.status == user.AccountStatus.ACTIVE
