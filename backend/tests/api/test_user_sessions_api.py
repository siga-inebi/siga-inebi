"""
ADR-0011, riesgo A: registro de sesiones (`UserSession`) y decisiones D1-D4.

Las sesiones ya no se encuentran decodificando todas las sesiones de Django:
se registran al iniciar sesion, se actualizan como maximo una vez por minuto,
se cierran (nunca se borran) al salir, al cerrarlas o al vencer, y se pueden
cerrar de a una.
"""

from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.db import connection
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.identity.atomic_permissions import PERMISSION_DETAILS, permission_codename
from apps.identity.models import UserSession
from apps.identity.services import (
    SESSION_TOUCH_KEY,
    describe_user_agent,
    touch_user_session,
)
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]

CHROME_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


def grant(user, *codes):
    permissions = [PermissionFactory(codename=permission_codename(code)) for code in codes]
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=permissions))


def login(username, password="clave-segura-1234", agent=CHROME_WINDOWS):
    client = Client(HTTP_USER_AGENT=agent, REMOTE_ADDR="10.1.2.3")
    response = client.post(reverse("auth-login"), {"username": username, "password": password})
    assert response.status_code == 200
    return client


# --------------------------------------------------------------------------- #
# Riesgo A: registro y ciclo de vida
# --------------------------------------------------------------------------- #


def test_login_registers_session_with_device_and_ip():
    user = UserFactory(password="clave-segura-1234")

    client = login(user.username)

    record = UserSession.objects.get(account=user)
    assert record.session_key == client.session.session_key
    assert record.ip_address == "10.1.2.3"
    assert record.user_agent == CHROME_WINDOWS
    assert record.ended_at is None
    assert describe_user_agent(record.user_agent) == "Chrome en Windows"


def test_user_agent_is_truncated():
    user = UserFactory(password="clave-segura-1234")

    login(user.username, agent="X" * 600)

    assert len(UserSession.objects.get(account=user).user_agent) == 255


def test_last_seen_is_written_at_most_once_per_minute():
    user = UserFactory()
    record = UserSession.objects.create(
        account=user, session_key="k-throttle", last_seen_at=timezone.now() - timedelta(hours=1)
    )
    request = RequestFactory().get("/")

    class FakeSession(dict):
        session_key = "k-throttle"

    request.session = FakeSession()
    start = timezone.now()

    assert touch_user_session(request=request, user=user, now=start) is True
    assert (
        touch_user_session(request=request, user=user, now=start + timedelta(seconds=30)) is False
    )
    record.refresh_from_db()
    assert record.last_seen_at == start
    assert touch_user_session(request=request, user=user, now=start + timedelta(seconds=61)) is True
    record.refresh_from_db()
    assert record.last_seen_at == start + timedelta(seconds=61)


def test_session_opened_before_the_table_is_registered_on_next_request(client):
    user = UserFactory()
    client.force_login(user)
    UserSession.objects.filter(account=user).update(ended_at=timezone.now())
    key = client.session.session_key
    # Simula una sesion previa al despliegue: sin fila abierta.
    UserSession.objects.filter(session_key=key).update(session_key="legacy-moved")
    session = client.session
    session.pop(SESSION_TOUCH_KEY, None)
    session.save()

    client.get(reverse("auth-me"))

    assert UserSession.objects.filter(session_key=key, ended_at__isnull=True).exists()


def test_logout_marks_session_ended_and_keeps_the_row():
    user = UserFactory(password="clave-segura-1234")
    client = login(user.username)

    client.post(reverse("auth-logout"))

    record = UserSession.objects.get(account=user)
    assert record.ended_at is not None
    assert record.end_reason == "logout"


def test_logout_all_and_idle_expiry_record_their_reason():
    user = UserFactory(password="clave-segura-1234")
    RoleAssignmentFactory(user=user, role=RoleFactory(session_idle_timeout_minutes=1))
    first = login(user.username)
    second = login(user.username)

    session = second.session
    session["identity.session_last_activity_at"] = (
        timezone.now() - timedelta(minutes=2)
    ).isoformat()
    session.save()
    assert second.get(reverse("auth-me")).status_code == 401
    first.post(reverse("auth-logout-all"))

    reasons = set(UserSession.objects.filter(account=user).values_list("end_reason", flat=True))
    assert reasons == {"expired", "logout_all"}


def test_session_rows_are_history():
    record = UserSession.objects.create(
        account=UserFactory(), session_key="k-history", last_seen_at=timezone.now()
    )

    with pytest.raises(RuntimeError):
        record.delete()


def test_my_account_lists_sessions_without_session_keys():
    user = UserFactory(password="clave-segura-1234")
    login(user.username, agent="Mozilla/5.0 (iPhone) Safari/604.1")
    client = login(user.username)

    sessions = client.get(reverse("identity-my-account")).json()["sessions"]

    assert len(sessions) == 2
    assert {item["device"] for item in sessions} == {"Chrome en Windows", "Safari en iPhone"}
    assert all("session_key" not in item for item in sessions)
    assert sum(item["is_current"] for item in sessions) == 1
    assert sessions[0]["ip_address"] == "10.1.2.3"
    assert sessions[0]["started_at"]


def test_owner_closes_one_of_their_sessions():
    user = UserFactory(password="clave-segura-1234")
    other_device = login(user.username)
    client = login(user.username)
    other = UserSession.objects.get(session_key=other_device.session.session_key)

    response = client.post(reverse("identity-my-session-close", args=[other.public_id]))

    assert response.status_code == 204
    other.refresh_from_db()
    assert other.end_reason == "closed_by_owner"
    assert not Session.objects.filter(session_key=other.session_key).exists()
    assert other_device.get(reverse("auth-me")).json()["authenticated"] is False
    assert client.get(reverse("auth-me")).json()["authenticated"] is True
    assert AuditEvent.objects.filter(action="identity.session.closed_single").exists()


def test_nobody_closes_another_accounts_session_from_my_account():
    victim = UserFactory(password="clave-segura-1234")
    login(victim.username)
    target = UserSession.objects.get(account=victim)
    intruder = UserFactory(password="clave-segura-1234")
    client = login(intruder.username)

    response = client.post(reverse("identity-my-session-close", args=[target.public_id]))

    assert response.status_code == 404
    target.refresh_from_db()
    assert target.ended_at is None


def test_administrator_closes_a_single_session_with_permission():
    target_user = UserFactory(password="clave-segura-1234")
    login(target_user.username)
    record = UserSession.objects.get(account=target_user)
    admin = UserFactory(password="clave-segura-1234")
    plain = UserFactory(password="clave-segura-1234")
    grant(admin, "account.disable")
    url = reverse("identity-account-session-close", args=[target_user.public_id, record.public_id])

    denied = login(plain.username).post(url)
    allowed = login(admin.username).post(url)

    assert denied.status_code == 403
    assert allowed.status_code == 204
    record.refresh_from_db()
    assert record.end_reason == "administrative"


def test_account_detail_lists_sessions_from_the_registry():
    target_user = UserFactory(password="clave-segura-1234")
    login(target_user.username)
    admin = UserFactory(password="clave-segura-1234")
    grant(admin, "account.disable")

    payload = (
        login(admin.username)
        .get(reverse("identity-account-detail", args=[target_user.public_id]))
        .json()
    )

    assert payload["sessions"][0]["device"] == "Chrome en Windows"
    assert payload["sessions"][0]["public_id"]


# --------------------------------------------------------------------------- #
# Decisiones D1-D4
# --------------------------------------------------------------------------- #


def test_d1_account_update_permission_edits_others_but_not_self():
    admin = UserFactory(password="clave-segura-1234")
    grant(admin, "account.update", "account.disable")
    client = login(admin.username)
    target = UserFactory(username="antes")

    edited = client.patch(
        reverse("identity-account-detail", args=[target.public_id]),
        {"username": "despues"},
        content_type="application/json",
    )
    self_edit = client.patch(
        reverse("identity-account-detail", args=[admin.public_id]),
        {"username": "otro"},
        content_type="application/json",
    )

    assert edited.status_code == 200
    assert self_edit.status_code == 403
    admin.refresh_from_db()
    assert admin.username != "otro"
    denial = AuditEvent.objects.get(action="identity.account.update_denied")
    assert denial.context["reason"] == "self_edit"


def test_d2_new_permissions_are_in_the_spanish_catalogue_and_seeded():
    from django.contrib.auth.models import Permission

    for code in ("account.update", "person.view", "person.edit", "document_type.manage"):
        assert PERMISSION_DETAILS[code]["label"]
        assert PERMISSION_DETAILS[code]["description"]
        assert Permission.objects.filter(codename=permission_codename(code)).exists()
    assert PERMISSION_DETAILS["person.view"]["group"] == "people"


def test_d3_audit_api_no_longer_exposes_or_filters_by_internal_actor_id():
    auditor = UserFactory(password="clave-segura-1234")
    grant(auditor, "audit.read")
    other = UserFactory()
    record_event(actor=other, action="test.d3", resource="R")
    client = login(auditor.username)

    rows = client.get(reverse("audit-event-list"), {"action": "test.d3"}).json()["results"]
    ignored = client.get(
        reverse("audit-event-list"), {"action": "test.d3", "actor_id": auditor.pk}
    ).json()

    assert "actor_id" not in rows[0]
    assert rows[0]["actor_public_id"] == str(other.public_id)
    assert ignored["count"] == 1  # el parametro obsoleto ya no filtra


def test_d4_disabled_account_cannot_receive_roles_with_clear_message():
    admin = UserFactory(password="clave-segura-1234")
    grant(admin, "role.assign")
    target = UserFactory(status="disabled", is_active=False)
    role = RoleFactory()

    response = login(admin.username).post(
        reverse("identity-role-assignment-create", args=[target.public_id]),
        {"role": str(role.public_id), "scope": {"module_key": "students"}},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["detail"] == "Reactive la cuenta antes de asignarle roles."


# --------------------------------------------------------------------------- #
# Riesgo B: indices de la bitacora
# --------------------------------------------------------------------------- #


def test_audit_event_has_console_indexes():
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "audit_auditevent")
    names = set(constraints)
    assert {
        "audit_action_recent_idx",
        "audit_actor_recent_idx",
        "audit_resource_recent_idx",
        "audit_recent_idx",
        "audit_action_prefix_idx",
    } <= names
