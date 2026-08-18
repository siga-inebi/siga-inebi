from unittest.mock import patch

import pytest

from apps.audit.models import AuditEvent
from apps.audit.services import record_event, record_sensitive_read, sanitize_context
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# --------------------------------------------------------------------------- #
# sanitize_context
# --------------------------------------------------------------------------- #


def test_sanitize_context_redacts_top_level_sensitive_keys():
    result = sanitize_context({"password": "secret", "safe": "ok"})

    assert "password" not in result
    assert result["safe"] == "ok"


def test_sanitize_context_redacts_nested_dict_values():
    result = sanitize_context({"user": {"token": "abc123", "username": "demo"}})

    assert "token" not in result["user"]
    assert result["user"]["username"] == "demo"


def test_sanitize_context_redacts_dicts_nested_in_lists():
    result = sanitize_context({"events": [{"secret": "x", "id": 1}, {"id": 2}]})

    assert "secret" not in result["events"][0]
    assert result["events"][0]["id"] == 1
    assert result["events"][1]["id"] == 2


def test_sanitize_context_key_match_is_case_insensitive():
    result = sanitize_context({"Password": "secret", "ACCESS_TOKEN": "abc"})

    assert "Password" not in result
    assert "ACCESS_TOKEN" not in result


# --------------------------------------------------------------------------- #
# record_event
# --------------------------------------------------------------------------- #


def test_record_event_captures_actor_label_from_username():
    actor = UserFactory(username="demo-user")

    event = record_event(actor=actor, action="test.action", resource="Resource")

    assert event.actor_id == actor.id
    assert event.actor_label == "demo-user"


def test_record_event_without_actor_has_blank_label():
    event = record_event(actor=None, action="test.action", resource="Resource")

    assert event.actor is None
    assert event.actor_label == ""


@patch("apps.audit.services.get_audit_context", return_value={})
def test_record_event_context_defaults_to_empty_dict(_mock_context):
    """
    ``get_audit_context`` reads a thread-local the request middleware
    populates; patched here so this test is isolated from whatever a
    previous test in the same worker last set it to.
    """
    event = record_event(actor=None, action="test.action", resource="Resource")

    assert event.context == {}


def test_record_event_sanitizes_supplied_context():
    event = record_event(
        actor=None,
        action="test.action",
        resource="Resource",
        context={"password": "secret", "reason": "manual_entry"},
    )

    assert "password" not in event.context
    assert event.context["reason"] == "manual_entry"


def test_record_event_explicit_ip_address_wins_over_context_value():
    event = record_event(
        actor=None,
        action="test.action",
        resource="Resource",
        context={"ip_address": "10.0.0.1"},
        ip_address="192.168.1.1",
    )

    assert event.ip_address == "192.168.1.1"


def test_record_event_falls_back_to_context_ip_address():
    event = record_event(
        actor=None,
        action="test.action",
        resource="Resource",
        context={"ip_address": "10.0.0.1"},
    )

    assert event.ip_address == "10.0.0.1"


# --------------------------------------------------------------------------- #
# record_sensitive_read -- RF-BIT-003
# --------------------------------------------------------------------------- #


def test_record_sensitive_read_captures_the_identified_student():
    actor = UserFactory()
    student = StudentFactory()

    event = record_sensitive_read(
        actor=actor,
        action="students.emergency_contacts.read",
        resource="EmergencyContact",
        resource_identifier=str(student.pk),
        student=student,
    )

    assert event.actor_id == actor.id
    assert event.action == "students.emergency_contacts.read"
    assert event.context["student_id"] == student.pk
    assert event.context["result"] == "success"


def test_record_sensitive_read_creates_a_real_audit_event():
    student = StudentFactory()

    record_sensitive_read(
        actor=None,
        action="attendance.day_status.read",
        resource="Student",
        resource_identifier=str(student.pk),
        student=student,
    )

    assert AuditEvent.objects.filter(action="attendance.day_status.read").exists()
