from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.academics.services import create_teaching_assignment, reassign_teaching_assignment
from apps.audit.models import AuditEvent
from apps.common.exceptions import AuthorizationError
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment
from apps.enrolments.services import create_enrolment
from apps.identity.services import assign_role, create_account, disable_account, protect_system_role
from apps.students.services import (
    change_primary_student_guardian_relation,
    create_student_guardian_relation,
    end_student_guardian_relation,
    guardian_can_access_student,
)
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
from tests.factories.people import PersonFactory
from tests.factories.students import GuardianFactory, StudentFactory, StudentGuardianRelationFactory
from tests.factories.teachers import TeacherFactory


@pytest.mark.permissions
@pytest.mark.django_db
def test_default_deny_without_assignments():
    user = UserFactory()

    assert user.has_atomic_permission("student_view_basic") is False


@pytest.mark.permissions
@pytest.mark.django_db
def test_permission_without_explicit_scope_is_denied():
    permission = PermissionFactory(codename="student_view_basic")
    assignment = RoleAssignmentFactory(
        role=RoleFactory(permissions=[permission]),
        identity_scope=False,
    )

    assert (
        assignment.user.has_scoped_permission(
            "student_view_basic",
            scope={"module_key": "students"},
        )
        is False
    )


@pytest.mark.permissions
@pytest.mark.django_db(transaction=True)
def test_database_rejects_active_scope_grant_without_dimension():
    assignment = RoleAssignmentFactory(identity_scope=False)

    with pytest.raises(IntegrityError), transaction.atomic():
        ScopeGrantFactory(assignment=assignment)


@pytest.mark.permissions
@pytest.mark.django_db
def test_role_groups_permission():
    permission = PermissionFactory(codename="student_view_basic")
    role = RoleFactory(permissions=[permission])
    assignment = RoleAssignmentFactory(role=role)

    assert (
        assignment.user.has_scoped_permission(
            "student_view_basic", scope={"module_key": "identity"}
        )
        is True
    )


@pytest.mark.permissions
@pytest.mark.django_db
def test_multiple_roles_union_permissions():
    read_permission = PermissionFactory(codename="student_view_basic")
    audit_permission = PermissionFactory(codename="audit_read")
    user = UserFactory()
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[read_permission]))
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[audit_permission]))

    assert (
        user.has_scoped_permission("student_view_basic", scope={"module_key": "identity"}) is True
    )
    assert user.has_scoped_permission("audit_read", scope={"module_key": "identity"}) is True


@pytest.mark.permissions
@pytest.mark.django_db
def test_scope_limits_permission():
    permission = PermissionFactory(codename="student_view_basic")
    institution = InstitutionFactory()
    assignment = RoleAssignmentFactory(
        role=RoleFactory(permissions=[permission]),
    )
    allowed_section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    denied_section = SectionFactory(academic_cycle=allowed_section.academic_cycle)
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
def test_contextual_permission_without_scope_grant_is_denied():
    permission = PermissionFactory(codename="student_view_basic")
    assignment = RoleAssignmentFactory(role=RoleFactory(permissions=[permission]))

    assert assignment.user.has_atomic_permission("student_view_basic") is True
    assert assignment.user.has_scoped_permission("student_view_basic") is False
    assert not assignment.user.has_scoped_permission(
        "student_view_basic",
        scope={"student": StudentFactory()},
    )


@pytest.mark.permissions
@pytest.mark.django_db
def test_institution_scope_matches_its_sections():
    permission = PermissionFactory(codename="student_view_basic")
    institution = InstitutionFactory()
    assignment = RoleAssignmentFactory(role=RoleFactory(permissions=[permission]))
    allowed_section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    denied_section = SectionFactory()
    ScopeGrantFactory(assignment=assignment, institution=institution)

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
    teacher = TeacherFactory()
    assignment = RoleAssignmentFactory(
        user=UserFactory(person=teacher.person),
        role=RoleFactory(permissions=[permission]),
    )
    section = SectionFactory()
    teaching_assignment = section.teaching_assignments.create(
        academic_cycle=section.academic_cycle,
        section=section,
        subject=section.academic_cycle.institution.subjects.create(name="Math", code="MATH"),
        teacher=teacher.person,
    )

    assert assignment.user.has_scoped_permission(
        "grade_capture",
        scope={"teaching_assignment": teaching_assignment},
    )


@pytest.mark.permissions
@pytest.mark.django_db
def test_teaching_assignment_grants_current_section_students_without_scope_grant():
    today = timezone.localdate()
    cycle = AcademicCycleFactory(
        starts_on=today - timedelta(days=1),
        ends_on=today + timedelta(days=10),
    )
    assigned_section = SectionFactory(academic_cycle=cycle)
    other_section = SectionFactory(academic_cycle=cycle)
    teacher = TeacherFactory()
    user = UserFactory(person=teacher.person)
    permission = PermissionFactory(codename="student_view_basic")
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    create_teaching_assignment(
        academic_cycle=cycle,
        section=assigned_section,
        subject=SubjectFactory(institution=cycle.institution),
        teacher=teacher.person,
        starts_on=today,
    )
    assigned_student = StudentFactory()
    other_student = StudentFactory()
    inactive_enrolment_student = StudentFactory()
    create_enrolment(
        student=assigned_student,
        academic_cycle=cycle,
        grade=assigned_section.grade,
        section=assigned_section,
    )
    create_enrolment(
        student=other_student,
        academic_cycle=cycle,
        grade=other_section.grade,
        section=other_section,
    )
    inactive_enrolment = create_enrolment(
        student=inactive_enrolment_student,
        academic_cycle=cycle,
        grade=assigned_section.grade,
        section=assigned_section,
    )
    inactive_enrolment.status = Enrolment.EnrolmentStatus.WITHDRAWN
    inactive_enrolment.save(update_fields=["status", "updated_at"])

    from apps.identity.scopes import authorized_student_queryset

    visible_ids = set(
        authorized_student_queryset(user=user, codename="student_view_basic").values_list(
            "pk", flat=True
        )
    )

    assert visible_ids == {assigned_student.pk}
    assert user.has_scoped_permission("student_view_basic", scope={"student": assigned_student})
    assert not user.has_scoped_permission("student_view_basic", scope={"student": other_student})
    assert not user.has_scoped_permission(
        "student_view_basic", scope={"student": inactive_enrolment_student}
    )

    cycle.status = cycle.CycleStatus.DRAFT
    cycle.save(update_fields=["status", "updated_at"])

    assert not user.has_scoped_permission("student_view_basic", scope={"student": assigned_student})


@pytest.mark.permissions
@pytest.mark.django_db
def test_reassignment_transfers_current_student_scope_to_successor_teacher():
    today = timezone.localdate()
    cycle = AcademicCycleFactory(
        starts_on=today - timedelta(days=1),
        ends_on=today + timedelta(days=10),
    )
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=cycle.institution)
    first_teacher = TeacherFactory()
    second_teacher = TeacherFactory()
    first_user = UserFactory(person=first_teacher.person)
    second_user = UserFactory(person=second_teacher.person)
    permission = PermissionFactory(codename="student_view_basic")
    RoleAssignmentFactory(user=first_user, role=RoleFactory(permissions=[permission]))
    RoleAssignmentFactory(user=second_user, role=RoleFactory(permissions=[permission]))
    assignment = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=first_teacher.person,
        starts_on=today - timedelta(days=1),
    )
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=cycle,
        grade=section.grade,
        section=section,
    )
    reassign_teaching_assignment(
        assignment=assignment,
        teacher=second_teacher.person,
        ends_on=today,
    )

    tomorrow = timezone.now() + timedelta(days=1)

    assert not first_user.has_scoped_permission(
        "student_view_basic", scope={"student": student}, when=tomorrow
    )
    assert second_user.has_scoped_permission(
        "student_view_basic", scope={"student": student}, when=tomorrow
    )


@pytest.mark.permissions
@pytest.mark.django_db
def test_teaching_assignment_scope_unites_with_administrative_scope():
    today = timezone.localdate()
    cycle = AcademicCycleFactory(
        starts_on=today - timedelta(days=1),
        ends_on=today + timedelta(days=10),
    )
    assigned_section = SectionFactory(academic_cycle=cycle)
    teacher = TeacherFactory()
    user = UserFactory(person=teacher.person)
    permission = PermissionFactory(codename="student_view_basic")
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    administrative_assignment = RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[permission]),
    )
    create_teaching_assignment(
        academic_cycle=cycle,
        section=assigned_section,
        subject=SubjectFactory(institution=cycle.institution),
        teacher=teacher.person,
        starts_on=today,
    )
    assigned_student = StudentFactory()
    administratively_scoped_student = StudentFactory()
    unrelated_student = StudentFactory()
    create_enrolment(
        student=assigned_student,
        academic_cycle=cycle,
        grade=assigned_section.grade,
        section=assigned_section,
    )
    ScopeGrantFactory(assignment=administrative_assignment, student=administratively_scoped_student)

    from apps.identity.scopes import authorized_student_queryset

    visible_ids = set(
        authorized_student_queryset(user=user, codename="student_view_basic").values_list(
            "pk", flat=True
        )
    )

    assert visible_ids == {assigned_student.pk, administratively_scoped_student.pk}
    assert unrelated_student.pk not in visible_ids


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
def test_guardian_scope_has_only_current_related_students_without_scope_grant():
    permission = PermissionFactory(codename="student_view_basic")
    guardian = GuardianFactory()
    guardian_user = UserFactory(person=guardian.person)
    RoleAssignmentFactory(user=guardian_user, role=RoleFactory(permissions=[permission]))
    first_student = StudentFactory()
    second_student = StudentFactory()
    unrelated_student = StudentFactory()
    create_student_guardian_relation(
        student=first_student,
        guardian=guardian,
        relationship_label="Madre",
    )
    create_student_guardian_relation(
        student=second_student,
        guardian=guardian,
        relationship_label="Madre",
    )

    from apps.identity.scopes import authorized_student_queryset

    visible_ids = set(
        authorized_student_queryset(
            user=guardian_user,
            codename="student_view_basic",
        ).values_list("pk", flat=True)
    )

    assert visible_ids == {first_student.pk, second_student.pk}
    assert unrelated_student.pk not in visible_ids
    assert guardian_user.has_scoped_permission(
        "student_view_basic", scope={"student": first_student}
    )
    assert not guardian_user.has_scoped_permission(
        "student_view_basic", scope={"student": unrelated_student}
    )


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_ended_guardian_relationship_never_restores_historical_access():
    permission = PermissionFactory(codename="student_view_basic")
    guardian = GuardianFactory()
    guardian_user = UserFactory(person=guardian.person)
    RoleAssignmentFactory(user=guardian_user, role=RoleFactory(permissions=[permission]))
    ended_student = StudentFactory()
    current_student = StudentFactory()
    replacement_guardian = GuardianFactory()
    ended_relation = create_student_guardian_relation(
        student=ended_student,
        guardian=guardian,
        relationship_label="Madre",
    )
    replacement_relation = create_student_guardian_relation(
        student=ended_student,
        guardian=replacement_guardian,
        relationship_label="Tutor",
    )
    create_student_guardian_relation(
        student=current_student,
        guardian=guardian,
        relationship_label="Madre",
    )
    change_primary_student_guardian_relation(relation=replacement_relation)
    end_student_guardian_relation(
        relation=ended_relation,
        replacement_relation=replacement_relation,
    )

    from apps.identity.scopes import authorized_student_queryset, can_access_student

    visible_ids = set(
        authorized_student_queryset(
            user=guardian_user,
            codename="student_view_basic",
        ).values_list("pk", flat=True)
    )
    assert visible_ids == {current_student.pk}
    assert (
        guardian_can_access_student(
            user=guardian_user,
            student=ended_student,
            when=ended_relation.starts_at,
        )
        is False
    )
    assert (
        can_access_student(
            user=guardian_user,
            codename="student_view_basic",
            student=ended_student,
        )
        is False
    )


@pytest.mark.permissions
@pytest.mark.django_db
def test_guardian_scope_unites_with_administrative_scope_without_other_students():
    permission = PermissionFactory(codename="student_view_basic")
    guardian = GuardianFactory()
    guardian_user = UserFactory(person=guardian.person)
    guardian_assignment = RoleAssignmentFactory(
        user=guardian_user,
        role=RoleFactory(permissions=[permission]),
    )
    administrative_assignment = RoleAssignmentFactory(
        user=guardian_user,
        role=RoleFactory(permissions=[permission]),
    )
    guardian_student = StudentFactory()
    administrative_student = StudentFactory()
    unrelated_student = StudentFactory()
    create_student_guardian_relation(
        student=guardian_student,
        guardian=guardian,
        relationship_label="Madre",
    )
    ScopeGrantFactory(assignment=administrative_assignment, student=administrative_student)

    from apps.identity.scopes import authorized_student_queryset

    visible_ids = set(
        authorized_student_queryset(
            user=guardian_user,
            codename="student_view_basic",
        ).values_list("pk", flat=True)
    )

    assert guardian_assignment.user_id == guardian_user.pk
    assert visible_ids == {guardian_student.pk, administrative_student.pk}
    assert unrelated_student.pk not in visible_ids


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

    assert user.has_scoped_permission("student_view_basic", scope={"section": allowed_section})
    assert user.has_scoped_permission("student_view_basic", scope={"section": second_allowed})
    assert (
        user.has_scoped_permission("student_view_basic", scope={"section": denied_section}) is False
    )


@pytest.mark.permissions
@pytest.mark.django_db
def test_authorization_changes_apply_immediately():
    permission = PermissionFactory(codename="audit_read")
    role = RoleFactory(permissions=[permission])
    assignment = RoleAssignmentFactory(role=role)

    assert (
        assignment.user.has_scoped_permission("audit_read", scope={"module_key": "identity"})
        is True
    )

    assignment.ends_at = assignment.starts_at
    assignment.save(update_fields=["ends_at", "updated_at"])

    assert (
        assignment.user.has_atomic_permission(
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

    with pytest.raises(AuthorizationError):
        assign_role(actor=actor, user=actor, role=role)


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_system_roles_require_explicit_authorization_to_modify():
    role = RoleFactory(is_system=True)
    actor = UserFactory(is_superuser=False)

    with pytest.raises(DomainError):
        protect_system_role(actor=actor, role=role)


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_authorized_actor_disables_account_without_deleting_it():
    permission = PermissionFactory(codename="account_disable")
    actor = UserFactory()
    RoleAssignmentFactory(user=actor, role=RoleFactory(permissions=[permission]))
    target = UserFactory()

    result = disable_account(actor=actor, user=target)

    target.refresh_from_db()
    assert result["account"].pk == target.pk
    assert target.status == target.AccountStatus.DISABLED
    assert target.is_active is False
    assert target.__class__.objects.filter(pk=target.pk).exists()

    event = AuditEvent.objects.get(action="identity.account.disabled")
    assert event.actor == actor
    assert event.resource == "UserAccount"
    assert event.resource_identifier == str(target.pk)
    assert event.context["target_user_id"] == target.pk


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_unauthorized_account_disable_is_denied_and_audited():
    actor = UserFactory()
    target = UserFactory()

    with pytest.raises(AuthorizationError):
        disable_account(actor=actor, user=target)

    target.refresh_from_db()
    assert target.status == target.AccountStatus.ACTIVE
    assert target.is_active is True

    event = AuditEvent.objects.get(action="identity.account.disable_denied")
    assert event.actor == actor
    assert event.resource_identifier == str(target.pk)
    assert event.context["target_user_id"] == target.pk
    assert event.context["result"] == "denied"


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_authorized_actor_creates_pending_account_linked_to_person():
    permission = PermissionFactory(codename="account_create")
    actor = UserFactory()
    RoleAssignmentFactory(user=actor, role=RoleFactory(permissions=[permission]))
    person = PersonFactory(email="new-account@example.test")

    account = create_account(actor=actor, person=person, username="new-account")

    assert account.person == person
    assert account.email == person.email
    assert account.status == account.AccountStatus.PENDING
    assert account.is_active is False
    assert account.has_usable_password() is False

    event = AuditEvent.objects.get(action="identity.account.created")
    assert event.actor == actor
    assert event.resource_identifier == str(account.pk)
    assert event.context["person_id"] == person.pk
    assert event.context["result"] == "success"


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_unauthorized_account_creation_is_denied_and_audited():
    actor = UserFactory()
    person = PersonFactory()

    with pytest.raises(AuthorizationError):
        create_account(actor=actor, person=person, username="denied-account")

    assert not person.__class__.objects.filter(pk=person.pk, user_account__isnull=False).exists()
    event = AuditEvent.objects.get(action="identity.account.create_denied")
    assert event.actor == actor
    assert event.context["person_id"] == person.pk
    assert event.context["reason"] == "missing_permission"


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_person_cannot_be_linked_to_multiple_accounts():
    actor = UserFactory(is_superuser=True)
    person = PersonFactory()
    create_account(actor=actor, person=person, username="first-account")

    with pytest.raises(DomainError, match="already has an account"):
        create_account(actor=actor, person=person, username="second-account")


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_rf_aut_006_unauthenticated_user_cannot_change_password():
    """RF-AUT-006: Solo el usuario autenticado (titular) puede cambiar su contraseña."""
    from apps.identity.services import change_password

    with pytest.raises(AuthorizationError):
        change_password(
            user=None,
            current_password="old-pass",
            new_password="New-Pass-2026!",
        )


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_rf_aut_002_locked_account_cannot_authenticate():
    """RF-AUT-002: Cuenta bloqueada temporalmente es rechazada al intentar autenticarse."""
    from apps.identity.services import AccountTemporarilyLockedError, authenticate_account

    user = UserFactory(password="secure-pass-123")
    user.failed_login_attempts = 5
    user.locked_until = timezone.now() + timedelta(minutes=10)
    user.save(update_fields=["failed_login_attempts", "locked_until"])

    with pytest.raises(AccountTemporarilyLockedError):
        authenticate_account(request=None, username=user.username, password="secure-pass-123")


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_rf_alc_005_teacher_cannot_write_in_closed_cycle():
    """RF-ALC-005: Intento de modificar calificaciones en un ciclo cerrado es denegado."""
    cycle = AcademicCycleFactory(status="active")
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=cycle.institution)
    teacher = TeacherFactory()
    teacher_person = teacher.person
    user = UserFactory(person=teacher_person)
    write_permission = PermissionFactory(codename="grade_write")
    correct_permission = PermissionFactory(codename="grade_correct")
    RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[write_permission, correct_permission]),
    )
    assignment = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher_person,
    )

    # El ciclo se cierra
    cycle.status = cycle.CycleStatus.CLOSED
    cycle.save(update_fields=["status", "updated_at"])
    assignment.refresh_from_db()
    section.refresh_from_db()

    # Intento de escribir o corregir en el ciclo cerrado
    assert (
        user.has_scoped_permission("grade_write", scope={"teaching_assignment": assignment})
        is False
    )
    assert (
        user.has_scoped_permission("grade_write", scope={"section": section, "subject": subject})
        is False
    )
    assert (
        user.has_scoped_permission("grade_correct", scope={"teaching_assignment": assignment})
        is False
    )


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_rf_alc_005_teacher_can_write_in_active_cycle():
    """RF-ALC-005: Escritura permitida para docente con asignación vigente en ciclo activo."""
    active_cycle = AcademicCycleFactory(status="active")
    section = SectionFactory(academic_cycle=active_cycle)
    subject = SubjectFactory(institution=active_cycle.institution)
    teacher = TeacherFactory()
    teacher_person = teacher.person
    user = UserFactory(person=teacher_person)
    write_permission = PermissionFactory(codename="grade_write")
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[write_permission]))
    assignment = create_teaching_assignment(
        academic_cycle=active_cycle,
        section=section,
        subject=subject,
        teacher=teacher_person,
    )

    assert (
        user.has_scoped_permission("grade_write", scope={"teaching_assignment": assignment}) is True
    )
    assert (
        user.has_scoped_permission("grade_write", scope={"section": section, "subject": subject})
        is True
    )


@pytest.mark.permissions
@pytest.mark.security
@pytest.mark.django_db
def test_rf_alc_005_administrative_write_denied_in_closed_cycle_but_read_allowed():
    """RF-ALC-005: Scope administrativo no permite escrituras en ciclos cerrados."""
    closed_cycle = AcademicCycleFactory(status="closed")
    section = SectionFactory(academic_cycle=closed_cycle)
    user = UserFactory()
    write_perm = PermissionFactory(codename="grade_write")
    read_perm = PermissionFactory(codename="student_view_basic")
    role = RoleFactory(permissions=[write_perm, read_perm])
    assignment = RoleAssignmentFactory(user=user, role=role)
    ScopeGrantFactory(assignment=assignment, section=section)

    # Escritura denegada en ciclo cerrado
    assert user.has_scoped_permission("grade_write", scope={"section": section}) is False

    # Lectura permitida
    assert user.has_scoped_permission("student_view_basic", scope={"section": section}) is True
