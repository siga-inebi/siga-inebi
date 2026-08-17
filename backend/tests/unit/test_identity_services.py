import pytest
from django.core.exceptions import PermissionDenied

from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment
from apps.identity.services import (
    assign_role,
    create_role,
    disable_account,
    filter_queryset_by_scope,
    list_atomic_permissions,
    revoke_role_assignment,
    update_role,
)
from apps.students.models import Student
from tests.factories.academic import SectionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.students import StudentFactory


@pytest.mark.django_db
def test_permission_catalog_requires_administrative_permission():
    actor = UserFactory()

    with pytest.raises(PermissionDenied):
        list_atomic_permissions(actor=actor)

    event = AuditEvent.objects.get(action="identity.permission_catalog.read_denied")
    assert event.actor == actor
    assert event.context["reason"] == "missing_permission"


@pytest.mark.django_db
def test_permission_catalog_returns_only_registered_atomic_permissions():
    actor = UserFactory()
    role_assign = PermissionFactory(codename="role_assign")
    RoleAssignmentFactory(user=actor, role=RoleFactory(permissions=[role_assign]))
    PermissionFactory(codename="unregistered_permission")

    permissions = list(list_atomic_permissions(actor=actor))

    codenames = {permission.codename for permission in permissions}
    assert "role_assign" in codenames
    assert "attendance_record_entry" in codenames
    assert "attendance_record_exit" in codenames
    assert "attendance_declared_close" in codenames
    assert "unregistered_permission" not in codenames
    event = AuditEvent.objects.get(action="identity.permission_catalog.read")
    assert event.context["permission_count"] == len(permissions)


@pytest.mark.django_db
def test_role_composition_change_applies_to_assigned_accounts_and_is_audited():
    actor = UserFactory(is_superuser=True)
    target = UserFactory()
    role = create_role(
        actor=actor,
        name="Attendance Operator",
        slug="attendance-operator-custom",
        permission_codenames=["attendance_record_entry"],
    )
    assignment = RoleAssignmentFactory(user=target, role=role)

    assert (
        target.has_scoped_permission("attendance_record_exit", scope={"module_key": "identity"})
        is False
    )

    update_role(
        actor=actor,
        role=role,
        permission_codenames=["attendance_record_entry", "attendance_record_exit"],
    )

    assert (
        target.has_scoped_permission("attendance_record_exit", scope={"module_key": "identity"})
        is True
    )
    event = AuditEvent.objects.get(action="identity.role.updated")
    assert event.actor == actor
    assert event.context["before"]["permissions"] == ["attendance_record_entry"]
    assert event.context["after"]["permissions"] == [
        "attendance_record_entry",
        "attendance_record_exit",
    ]
    assert assignment.user_id == target.pk


@pytest.mark.django_db
def test_revoked_role_is_denied_on_next_permission_evaluation():
    actor = UserFactory(is_superuser=True)
    target = UserFactory()
    permission = PermissionFactory(codename="audit_read")
    assignment = RoleAssignmentFactory(
        user=target,
        role=RoleFactory(permissions=[permission]),
    )

    assert target.has_scoped_permission("audit_read", scope={"module_key": "identity"}) is True

    revoke_role_assignment(actor=actor, assignment=assignment)

    assert target.has_scoped_permission("audit_read", scope={"module_key": "identity"}) is False
    assert AuditEvent.objects.filter(
        action="identity.role_assignment.revoked",
        actor=actor,
    ).exists()


@pytest.mark.django_db
def test_role_assignment_requires_explicit_scope():
    actor = UserFactory(is_superuser=True)

    with pytest.raises(DomainError, match="explicit scope"):
        assign_role(actor=actor, user=UserFactory(), role=RoleFactory(), scope=None)


@pytest.mark.django_db
def test_last_account_administrator_role_cannot_be_revoked():
    actor = UserFactory(is_superuser=True)
    account_create = PermissionFactory(codename="account_create")
    protected = RoleAssignmentFactory(
        role=RoleFactory(permissions=[account_create]),
    )

    with pytest.raises(DomainError, match="last account administrator"):
        revoke_role_assignment(actor=actor, assignment=protected)

    RoleAssignmentFactory(role=RoleFactory(permissions=[account_create]))
    revoked = revoke_role_assignment(actor=actor, assignment=protected)

    assert revoked.ends_at is not None


@pytest.mark.django_db
def test_last_administrator_role_cannot_lose_account_create_permission():
    actor = UserFactory(is_superuser=True)
    account_create = PermissionFactory(codename="account_create")
    protected_role = RoleFactory(permissions=[account_create])
    RoleAssignmentFactory(role=protected_role)

    with pytest.raises(DomainError, match="last account administrator"):
        update_role(actor=actor, role=protected_role, permission_codenames=[])

    RoleAssignmentFactory(role=RoleFactory(permissions=[account_create]))
    updated = update_role(actor=actor, role=protected_role, permission_codenames=[])

    assert updated.permissions.exists() is False


@pytest.mark.django_db
def test_last_account_administrator_cannot_be_disabled():
    actor = UserFactory(is_superuser=True)
    account_create = PermissionFactory(codename="account_create")
    protected = RoleAssignmentFactory(role=RoleFactory(permissions=[account_create])).user

    with pytest.raises(DomainError, match="last account administrator"):
        disable_account(actor=actor, user=protected)

    RoleAssignmentFactory(role=RoleFactory(permissions=[account_create]))
    disabled = disable_account(actor=actor, user=protected)

    assert disabled.is_active is False


@pytest.mark.django_db
def test_queryset_filter_only_returns_records_inside_effective_scope():
    permission = PermissionFactory(codename="student_view_basic")
    assignment = RoleAssignmentFactory(
        role=RoleFactory(permissions=[permission]),
        identity_scope=False,
    )
    allowed_section = SectionFactory()
    denied_section = SectionFactory()
    ScopeGrantFactory(assignment=assignment, section=allowed_section)
    allowed_student = StudentFactory()
    denied_student = StudentFactory()
    Enrolment.objects.create(
        student=allowed_student,
        academic_cycle=allowed_section.academic_cycle,
        grade=allowed_section.grade,
        section=allowed_section,
    )
    Enrolment.objects.create(
        student=denied_student,
        academic_cycle=denied_section.academic_cycle,
        grade=denied_section.grade,
        section=denied_section,
    )

    scoped_students = filter_queryset_by_scope(
        actor=assignment.user,
        codename="student_view_basic",
        queryset=Student.objects.all(),
        dimension="section",
        lookup="enrolments__section_id",
    )

    assert list(scoped_students) == [allowed_student]


# ---------------------------------------------------------------------------
# RF-CTA-004 — Política de contraseñas
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rf_cta_004_common_password_is_rejected():
    """Escenario 1: contraseña presente en la lista de comunes → rechazada."""
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    user = UserFactory()
    with pytest.raises(ValidationError) as exc_info:
        validate_password("password", user=user)
    assert any("común" in msg or "common" in msg for msg in exc_info.value.messages)


@pytest.mark.django_db
def test_rf_cta_004_long_password_without_symbols_is_accepted():
    """Escenario 2: contraseña larga sin símbolos, no común → aceptada."""
    from django.contrib.auth.password_validation import validate_password

    user = UserFactory()
    # Solo minúsculas, sin mayúsculas, números ni símbolos; supera longitud mínima.
    validate_password("alargadaycorrecta", user=user)
