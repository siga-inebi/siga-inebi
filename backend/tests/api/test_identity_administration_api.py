"""
docs/ux-ui.md 2.17 y ADR-0011: administracion de identidad y acceso.

Cubre los contratos que la interfaz necesita para dar acceso al sistema sin ids
internos (U1, RA1), la ficha y edicion de la cuenta (U4, U5, U7), reactivar y
desbloquear (D8 / RF-CTA-008), el retiro seguro de roles (RO1-RO6), los
alcances con public_id y el alcance docente automatico (RA1-RA5), los permisos
efectivos de ``/auth/me/`` (1.4) y las reglas reales de contraseña (MC2).
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import TeachingAssignment
from apps.audit.models import AuditEvent
from apps.identity.atomic_permissions import ATOMIC_PERMISSIONS, permission_codename
from apps.identity.models import ActivationChallenge, RoleAssignment, ScopeGrant
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
    UserFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def grant(user, *codes, **role_kwargs):
    permissions = [PermissionFactory(codename=permission_codename(code)) for code in codes]
    role = RoleFactory(permissions=permissions, **role_kwargs)
    RoleAssignmentFactory(user=user, role=role)
    return role


@pytest.fixture
def admin(client):
    user = UserFactory()
    grant(
        user,
        "account.create",
        "account.activate",
        "account.disable",
        "role.assign",
    )
    client.force_login(user)
    client.user = user
    return client


# --------------------------------------------------------------------------- #
# 1.4 permisos efectivos en /auth/me/
# --------------------------------------------------------------------------- #


def test_me_returns_public_id_effective_permissions_and_roles(client):
    user = UserFactory()
    role = grant(user, "student.view_basic", "audit.read", name="Secretaría")
    client.force_login(user)

    payload = client.get(reverse("auth-me")).json()["user"]

    assert "id" not in payload
    assert payload["public_id"] == str(user.public_id)
    assert payload["person"]["public_id"] == str(user.person.public_id)
    assert "id" not in payload["person"]
    assert payload["permissions"] == ["audit.read", "student.view_basic"]
    assert payload["roles"] == [
        {"public_id": str(role.public_id), "name": role.name, "slug": role.slug}
    ]
    assert payload["status_display"] == "Activa"
    assert payload["session_idle_timeout_minutes"] == role.session_idle_timeout_minutes
    assert payload["is_superuser"] is False


def test_me_excludes_permissions_of_retired_roles_and_ended_assignments(client):
    user = UserFactory()
    retired = grant(user, "audit.read")
    retired.is_active = False
    retired.save(update_fields=["is_active"])
    ended_role = RoleFactory(permissions=[PermissionFactory(codename="platform_monitor")])
    RoleAssignmentFactory(
        user=user,
        role=ended_role,
        starts_at=timezone.now() - timedelta(days=10),
        ends_at=timezone.now() - timedelta(days=1),
    )
    client.force_login(user)

    assert client.get(reverse("auth-me")).json()["user"]["permissions"] == []
    # La evaluacion real coincide con lo que se muestra.
    assert user.has_atomic_permission("audit_read") is False


def test_me_gives_superuser_the_whole_catalogue(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)

    permissions = client.get(reverse("auth-me")).json()["user"]["permissions"]

    assert permissions == sorted(code for code, _label in ATOMIC_PERMISSIONS)


# --------------------------------------------------------------------------- #
# RO2 catalogo en espanol, agrupado, con permisos nuevos
# --------------------------------------------------------------------------- #


def test_permission_catalogue_is_spanish_grouped_and_includes_new_permissions(admin):
    response = admin.get(reverse("identity-permission-list"), {"page_size": 100})

    assert response.status_code == 200
    rows = {row["code"]: row for row in response.json()["results"]}
    assert rows["student.view_basic"]["name"] == "Ver datos básicos del estudiante"
    assert rows["student.view_basic"]["group_label"] == "Estudiantes"
    assert rows["student.view_basic"]["description"]
    assert "academic_cycle.revert" in rows
    assert rows["retention_policy.declare"]["group"] == "audit"
    assert Permission.objects.get(codename="academic_cycle_revert").name == (
        "Volver un ciclo a borrador"
    )


def test_password_policy_is_public_and_lists_real_validator_rules(client):
    response = client.get(reverse("identity-password-policy"))

    assert response.status_code == 200
    rules = response.json()["rules"]
    assert len(rules) >= 3
    assert all(isinstance(rule, str) and rule for rule in rules)


# --------------------------------------------------------------------------- #
# U1 dar acceso por person_public_id, candidatas y usuario sugerido
# --------------------------------------------------------------------------- #


def test_provision_uses_person_public_id_and_rejects_internal_ids(admin):
    person = PersonFactory(first_name="Ana", last_name="López")

    rejected = admin.post(
        reverse("identity-account-provision"), {"person": person.pk, "username": "ana"}
    )
    assert rejected.status_code == 400

    response = admin.post(
        reverse("identity-account-provision"),
        {"person_public_id": str(person.public_id), "username": "ana.lopez"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert "id" not in payload
    assert payload["person_public_id"] == str(person.public_id)
    assert payload["status_display"] == "Pendiente"
    assert len(payload["activation_code"]) == 8


def test_candidates_list_people_without_account_searchable_by_name_or_cui(admin):
    candidate = PersonFactory(first_name="Ana María", last_name="López Pérez", cui="1234567890101")
    TeacherFactory(person=candidate)
    with_account = PersonFactory(first_name="Ana", last_name="Con Cuenta")
    UserFactory(person=with_account)

    by_name = admin.get(reverse("identity-account-candidates"), {"search": "Ana López"}).json()
    by_cui = admin.get(reverse("identity-account-candidates"), {"search": "1234567890101"}).json()

    names = [row["full_name"] for row in by_name["results"]]
    assert "Ana María López Pérez" in names
    assert "Ana Con Cuenta" not in names
    assert by_cui["results"][0]["public_id"] == str(candidate.public_id)
    assert by_cui["results"][0]["cui_hint"] == "…0101"
    assert by_cui["results"][0]["profiles"] == ["teacher"]


def test_candidates_require_account_create(client):
    user = UserFactory()
    grant(user, "account.disable")
    client.force_login(user)

    assert client.get(reverse("identity-account-candidates")).status_code == 403


def test_username_suggestion_is_first_name_dot_last_name_and_unique(admin):
    person = PersonFactory(first_name="José Luis", last_name="Pérez García")
    UserFactory(username="jose.perez")

    response = admin.get(reverse("identity-username-suggestion"), {"person": person.public_id})

    assert response.json() == {"username": "jose.perez2"}


# --------------------------------------------------------------------------- #
# U4/U5/U7 listado, ficha y edicion
# --------------------------------------------------------------------------- #


def test_account_list_filters_columns_and_no_internal_ids(admin):
    role = RoleFactory(name="Docente")
    locked = UserFactory(username="bloqueada", email="bloq@example.test")
    locked.locked_until = timezone.now() + timedelta(minutes=5)
    locked.failed_login_attempts = 5
    locked.save(update_fields=["locked_until", "failed_login_attempts"])
    teacher = UserFactory(username="docente1", email="profe@example.test")
    RoleAssignmentFactory(user=teacher, role=role)

    by_email = admin.get(reverse("identity-account-list"), {"search": "profe@"}).json()
    by_role = admin.get(reverse("identity-account-list"), {"role": role.public_id}).json()
    by_lock = admin.get(reverse("identity-account-list"), {"locked": "true"}).json()

    row = by_email["results"][0]
    assert "id" not in row
    assert row["public_id"] == str(teacher.public_id)
    assert row["email"] == "profe@example.test"
    assert row["roles"][0]["name"] == "Docente"
    assert row["status_display"] == "Activa"
    assert "last_login" in row and "locked_until" in row
    assert [r["username"] for r in by_role["results"]] == ["docente1"]
    assert [r["username"] for r in by_lock["results"]] == ["bloqueada"]
    assert by_lock["results"][0]["is_locked"] is True


def test_account_detail_includes_sessions_activity_and_pending_activation(admin):
    target = UserFactory(password="clave-segura-1234")
    Client().post(
        reverse("auth-login"), {"username": target.username, "password": "clave-segura-1234"}
    )

    payload = admin.get(reverse("identity-account-detail", args=[target.public_id])).json()

    assert payload["public_id"] == str(target.public_id)
    assert len(payload["sessions"]) == 1
    assert payload["sessions"][0]["is_current"] is False
    assert payload["recent_activity"][0]["action"] == "identity.login.succeeded"
    assert payload["activation_expires_at"] is None


def test_account_detail_is_denied_without_account_permissions(client):
    user = UserFactory()
    client.force_login(user)
    target = UserFactory()

    response = client.get(reverse("identity-account-detail", args=[target.public_id]))

    assert response.status_code == 403


def test_unknown_account_returns_spanish_404(admin):
    import uuid

    response = admin.get(reverse("identity-account-detail", args=[uuid.uuid4()]))

    assert response.status_code == 404
    assert response.json()["error"]["detail"]["detail"] == "No se encontró la cuenta."


def test_account_edit_changes_username_and_email_and_audits_changes(admin):
    target = UserFactory(username="antes", email="antes@example.test")
    UserFactory(username="ocupado")

    duplicate = admin.patch(
        reverse("identity-account-detail", args=[target.public_id]),
        {"username": "ocupado"},
        content_type="application/json",
    )
    response = admin.patch(
        reverse("identity-account-detail", args=[target.public_id]),
        {"username": "despues", "email": "despues@example.test"},
        content_type="application/json",
    )

    assert duplicate.status_code == 400
    assert response.status_code == 200
    target.refresh_from_db()
    assert (target.username, target.email) == ("despues", "despues@example.test")
    event = AuditEvent.objects.get(action="identity.account.updated")
    assert event.context["changes"]["username"] == {"before": "antes", "after": "despues"}


def test_account_edit_requires_account_create(client):
    user = UserFactory()
    grant(user, "account.disable")
    client.force_login(user)
    target = UserFactory(username="intacta")

    response = client.patch(
        reverse("identity-account-detail", args=[target.public_id]),
        {"username": "cambiada"},
        content_type="application/json",
    )

    assert response.status_code == 403
    target.refresh_from_db()
    assert target.username == "intacta"
    assert AuditEvent.objects.filter(action="identity.account.update_denied").exists()


# --------------------------------------------------------------------------- #
# D8 / RF-CTA-008 reactivar y desbloquear
# --------------------------------------------------------------------------- #


def test_reactivation_returns_disabled_account_to_pending_with_new_code(admin, client):
    target = UserFactory(password="vieja-clave-segura-1")
    revoked_role = RoleFactory()
    revoked = RoleAssignmentFactory(
        user=target,
        role=revoked_role,
        starts_at=timezone.now() - timedelta(days=5),
        ends_at=timezone.now() - timedelta(days=1),
    )
    target.status = get_user_model().AccountStatus.DISABLED
    target.is_active = False
    target.save(update_fields=["status", "is_active"])

    response = admin.post(
        reverse("identity-account-reactivate", args=[target.public_id]),
        {"reason": "Desactivada por error"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["account"]["status"] == "pending"
    assert payload["account"]["status_display"] == "Pendiente"
    assert len(payload["activation_code"]) == 8
    target.refresh_from_db()
    assert target.has_usable_password() is False
    revoked.refresh_from_db()
    assert revoked.ends_at < timezone.now()  # los roles revocados no vuelven solos
    event = AuditEvent.objects.get(action="identity.account.reactivated")
    assert event.context["reason"] == "Desactivada por error"
    assert event.context["roles_restored"] is False
    assert payload["activation_code"] not in str(event.context)

    client.logout()
    activation = client.post(
        reverse("identity-account-activate"),
        {
            "username": target.username,
            "activation_code": payload["activation_code"],
            "password": "nueva-clave-muy-segura-42",
        },
    )
    assert activation.status_code == 200
    target.refresh_from_db()
    assert target.status == "active"


def test_reactivation_requires_reason_disabled_status_and_permission(admin, client):
    disabled = UserFactory(status="disabled", is_active=False)
    active = UserFactory()

    no_reason = admin.post(reverse("identity-account-reactivate", args=[disabled.public_id]), {})
    not_disabled = admin.post(
        reverse("identity-account-reactivate", args=[active.public_id]), {"reason": "x"}
    )
    assert no_reason.status_code == 400
    assert not_disabled.status_code == 400
    assert "desactivada" in not_disabled.json()["error"]["detail"]

    plain = UserFactory()
    grant(plain, "account.disable")
    client.force_login(plain)
    denied = client.post(
        reverse("identity-account-reactivate", args=[disabled.public_id]), {"reason": "x"}
    )
    assert denied.status_code == 403
    disabled.refresh_from_db()
    assert disabled.status == "disabled"


def test_nobody_reactivates_or_unlocks_their_own_account(admin):
    own = admin.user

    assert (
        admin.post(reverse("identity-account-unlock", args=[own.public_id]), {"reason": "x"})
    ).status_code == 403


def test_unlock_clears_temporary_lock_and_is_audited(admin, client):
    target = UserFactory(password="clave-segura-1234")
    target.failed_login_attempts = 5
    target.locked_until = timezone.now() + timedelta(minutes=10)
    target.save(update_fields=["failed_login_attempts", "locked_until"])

    response = admin.post(
        reverse("identity-account-unlock", args=[target.public_id]),
        {"reason": "La persona se identificó en ventanilla"},
    )

    assert response.status_code == 200
    assert response.json()["is_locked"] is False
    target.refresh_from_db()
    assert (target.failed_login_attempts, target.locked_until) == (0, None)
    event = AuditEvent.objects.get(action="identity.account.unlocked")
    assert event.context["before"]["failed_login_attempts"] == 5
    client.logout()
    login = client.post(
        reverse("auth-login"), {"username": target.username, "password": "clave-segura-1234"}
    )
    assert login.status_code == 200


def test_unlock_rejects_account_that_is_not_locked(admin):
    target = UserFactory()

    response = admin.post(
        reverse("identity-account-unlock", args=[target.public_id]), {"reason": "x"}
    )

    assert response.status_code == 400
    assert response.json()["error"]["detail"] == "La cuenta no está bloqueada."


# --------------------------------------------------------------------------- #
# RO1-RO6 roles
# --------------------------------------------------------------------------- #


def test_role_slug_is_derived_from_name_and_names_are_unique(admin):
    first = admin.post(
        reverse("identity-role-list-create"),
        {"name": "Coordinación Académica", "permissions": ["audit.read"]},
        content_type="application/json",
    )
    duplicate = admin.post(
        reverse("identity-role-list-create"),
        {"name": "coordinación académica"},
        content_type="application/json",
    )

    assert first.status_code == 201
    assert first.json()["slug"] == "coordinacion-academica"
    assert duplicate.status_code == 400


def test_role_list_reports_account_counts_and_inactive_filter(admin):
    used = RoleFactory(name="Usado")
    RoleAssignmentFactory(role=used)
    RoleAssignmentFactory(role=used)
    retired = RoleFactory(name="Retirado", is_active=False)

    rows = {
        row["name"]: row
        for row in admin.get(reverse("identity-role-list-create"), {"page_size": 100}).json()[
            "results"
        ]
    }
    active_only = [
        row["name"]
        for row in admin.get(
            reverse("identity-role-list-create"), {"include_inactive": "false", "page_size": 100}
        ).json()["results"]
    ]

    assert rows["Usado"]["active_account_count"] == 2
    assert rows["Retirado"]["is_active"] is False
    assert retired.name not in active_only


def test_role_holders_and_permission_holders(admin):
    role = RoleFactory(name="Auditoría", permissions=[PermissionFactory(codename="audit_read")])
    holder = UserFactory(username="auditora")
    RoleAssignmentFactory(user=holder, role=role)

    holders = admin.get(reverse("identity-role-holders", args=[role.public_id])).json()
    by_permission = admin.get(reverse("identity-permission-holders", args=["audit.read"])).json()
    unknown = admin.get(reverse("identity-permission-holders", args=["nope.nope"]))

    assert [row["username"] for row in holders["results"]] == ["auditora"]
    assert "auditora" in [row["username"] for row in by_permission["results"]]
    assert unknown.status_code == 404


def test_role_cannot_be_retired_while_assigned_or_if_system(admin):
    assigned = RoleFactory()
    RoleAssignmentFactory(role=assigned)
    system = RoleFactory(is_system=True)

    blocked = admin.post(
        reverse("identity-role-deactivate", args=[assigned.public_id]), {"reason": "Ya no se usa"}
    )
    system_response = admin.post(
        reverse("identity-role-deactivate", args=[system.public_id]), {"reason": "x"}
    )

    assert blocked.status_code == 400
    assert "Revóquelas" in blocked.json()["error"]["detail"]
    assert system_response.status_code == 400


def test_unused_role_is_retired_not_deleted_and_cannot_be_assigned(admin):
    role = RoleFactory()
    target = UserFactory()

    retired = admin.post(
        reverse("identity-role-deactivate", args=[role.public_id]), {"reason": "Fusionado"}
    )
    assign = admin.post(
        reverse("identity-role-assignment-create", args=[target.public_id]),
        {"role": str(role.public_id), "scope": {"module_key": "students"}},
        content_type="application/json",
    )
    reactivated = admin.post(
        reverse("identity-role-reactivate", args=[role.public_id]), {"reason": "Se necesita"}
    )

    assert retired.status_code == 200
    assert retired.json()["is_active"] is False
    assert assign.status_code == 400
    assert reactivated.json()["is_active"] is True
    assert AuditEvent.objects.filter(action="identity.role.deactivated").exists()


# --------------------------------------------------------------------------- #
# RA1-RA5 asignaciones con alcance
# --------------------------------------------------------------------------- #


def test_assignment_scope_uses_public_ids_and_returns_readable_scope(admin):
    institution = InstitutionFactory()
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle)
    role = RoleFactory(name="Coordinación")
    target = UserFactory()

    rejected = admin.post(
        reverse("identity-role-assignment-create", args=[target.public_id]),
        {"role": str(role.public_id), "scope": {"section": section.pk}},
        content_type="application/json",
    )
    response = admin.post(
        reverse("identity-role-assignment-create", args=[target.public_id]),
        {
            "role": str(role.public_id),
            "scope": {"section": str(section.public_id), "academic_cycle": str(cycle.public_id)},
        },
        content_type="application/json",
    )

    assert rejected.status_code == 400
    assert response.status_code == 201
    payload = response.json()
    assert payload["account"] == str(target.public_id)
    assert payload["role_name"] == "Coordinación"
    assert payload["status"] == "active"
    dimensions = {part["dimension"]: part for part in payload["scopes"][0]["dimensions"]}
    assert dimensions["section"]["public_id"] == str(section.public_id)
    assert dimensions["academic_cycle"]["label"] == cycle.name

    listing = admin.get(reverse("identity-role-assignment-create", args=[target.public_id])).json()
    assert listing["results"][0]["public_id"] == payload["public_id"]


def test_assignment_rejects_unknown_module_key(admin):
    target = UserFactory()
    role = RoleFactory()

    response = admin.post(
        reverse("identity-role-assignment-create", args=[target.public_id]),
        {"role": str(role.public_id), "scope": {"module_key": "inventado"}},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_teacher_scope_uses_current_teaching_assignments(admin):
    teacher = TeacherFactory()
    account = UserFactory(person=teacher.person)
    role = RoleFactory(name="Docente", permissions=[PermissionFactory(codename="grade_write")])
    cycle = AcademicCycleFactory(status="active")
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory()
    TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
        starts_on=timezone.localdate() - timedelta(days=1),
    )
    not_teacher = UserFactory()

    denied = admin.post(
        reverse("identity-role-assignment-create", args=[not_teacher.public_id]),
        {"role": str(role.public_id), "scope": {"teaching_assignments": True}},
        content_type="application/json",
    )
    response = admin.post(
        reverse("identity-role-assignment-create", args=[account.public_id]),
        {"role": str(role.public_id), "scope": {"teaching_assignments": True}},
        content_type="application/json",
    )

    assert denied.status_code == 400
    assert response.status_code == 201
    module = response.json()["scopes"][0]["dimensions"][0]
    assert module["value"] == "teaching_assignments"
    assert module["label"] == "Sus asignaciones docentes vigentes"
    # El alcance real sale de la asignacion vigente (RF-ALC-002).
    assert account.has_scoped_permission(
        "grade_write", scope={"section": section, "subject": subject}
    )


def test_expiring_assignments_lists_upcoming_and_recently_ended(admin):
    soon = RoleAssignmentFactory(
        user=UserFactory(username="vence-pronto"), ends_at=timezone.now() + timedelta(days=5)
    )
    RoleAssignmentFactory(
        user=UserFactory(username="vence-lejos"), ends_at=timezone.now() + timedelta(days=60)
    )
    RoleAssignmentFactory(
        user=UserFactory(username="vencio"),
        starts_at=timezone.now() - timedelta(days=30),
        ends_at=timezone.now() - timedelta(days=3),
    )

    payload = admin.get(reverse("identity-role-assignment-expiring")).json()

    usernames = [row["username"] for row in payload["results"]]
    assert usernames == ["vencio", "vence-pronto"]
    statuses = {row["username"]: row["status"] for row in payload["results"]}
    assert statuses == {"vencio": "ended", "vence-pronto": "expiring"}
    assert str(soon.public_id) in [row["assignment"] for row in payload["results"]]


def test_revocation_keeps_history(admin):
    target = UserFactory()
    assignment = RoleAssignmentFactory(user=target)

    response = admin.delete(reverse("identity-role-assignment-revoke", args=[assignment.public_id]))

    assert response.status_code == 200
    assert response.json()["status"] == "ended"
    assert RoleAssignment.objects.filter(pk=assignment.pk).exists()
    assert ScopeGrant.objects.filter(assignment=assignment).exists()


# --------------------------------------------------------------------------- #
# MC1 / MC2 cuenta propia y reglas de contraseña
# --------------------------------------------------------------------------- #


def test_my_account_lists_roles_with_scope_labels_and_current_session(client):
    user = UserFactory(password="clave-segura-1234")
    role = grant(user, "student.view_basic", name="Secretaría")
    client.post(reverse("auth-login"), {"username": user.username, "password": "clave-segura-1234"})

    payload = client.get(reverse("identity-my-account")).json()

    assert payload["account"]["public_id"] == str(user.public_id)
    assert payload["roles"][0]["role_name"] == role.name
    assert payload["roles"][0]["scopes"][0]["dimensions"][0]["label"] == (
        "Administración de cuentas y accesos"
    )
    assert payload["sessions"][0]["is_current"] is True
    assert payload["permissions"] == ["student.view_basic"]


def test_activation_password_errors_are_reported_per_field(admin, client):
    person = PersonFactory()
    provisioned = admin.post(
        reverse("identity-account-provision"),
        {"person_public_id": str(person.public_id), "username": "campo.password"},
    ).json()
    client.logout()

    response = client.post(
        reverse("identity-account-activate"),
        {
            "username": "campo.password",
            "activation_code": provisioned["activation_code"],
            "password": "123",
        },
    )

    assert response.status_code == 400
    errors = response.json()["error"]["detail"]["password"]
    assert len(errors) >= 2
    assert ActivationChallenge.objects.get(account__public_id=provisioned["public_id"]).is_usable()


def test_password_reset_consume_reports_password_rules_per_field(admin, client):
    target = UserFactory()
    token = admin.post(reverse("identity-password-reset-issue", args=[target.public_id])).json()[
        "token"
    ]
    client.logout()

    response = client.post(
        reverse("identity-password-reset-consume"), {"token": token, "password": "1234"}
    )

    assert response.status_code == 400
    assert response.json()["error"]["detail"]["password"]


def test_successful_login_is_audited_for_access_history(client):
    user = UserFactory(password="clave-segura-1234")

    client.post(reverse("auth-login"), {"username": user.username, "password": "clave-segura-1234"})

    event = AuditEvent.objects.get(action="identity.login.succeeded")
    assert event.actor_id == user.pk


def test_scope_options_list_modules_and_institution_public_id(admin):
    institution = InstitutionFactory(name="Instituto Demo")

    payload = admin.get(reverse("identity-scope-options")).json()

    assert {"value": "students", "label": "Expedientes de estudiantes"} in payload["modules"]
    assert payload["institution"] == {
        "public_id": str(institution.public_id),
        "name": "Instituto Demo",
    }


def test_account_person_reports_teacher_flag(admin):
    teacher = TeacherFactory()
    account = UserFactory(person=teacher.person)

    payload = admin.get(reverse("identity-account-detail", args=[account.public_id])).json()

    assert payload["person"]["is_teacher"] is True


def test_locked_account_has_no_effective_permissions(client):
    from apps.identity.services import effective_permission_codes

    user = UserFactory()
    grant(user, "audit.read")
    user.locked_until = timezone.now() + timedelta(minutes=5)
    user.save(update_fields=["locked_until"])

    assert effective_permission_codes(user=user) == []
