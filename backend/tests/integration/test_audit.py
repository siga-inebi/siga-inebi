import pytest
from django.core.exceptions import PermissionDenied

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.enrolments.services import create_enrolment
from apps.identity.services import assign_role
from tests.factories.academic import SectionFactory
from tests.factories.identity import PermissionFactory, RoleFactory, UserFactory
from tests.factories.students import StudentFactory


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_sensitive_write_produces_audit_event():
    actor = UserFactory(is_superuser=True)
    student = StudentFactory()
    section = SectionFactory()

    create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        actor=actor,
    )

    event = AuditEvent.objects.latest("created_at")
    assert event.actor_id == actor.id
    assert event.action == "enrolments.enrolment.created"


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_audit_event_actor_persists_after_user_deleted():
    actor = UserFactory(is_superuser=True)
    event = record_event(
        actor=actor,
        action="test.action",
        resource="Resource",
        resource_identifier="1",
        context={"password": "secret", "safe": "ok"},
    )

    actor.delete()
    event.refresh_from_db()

    assert event.actor is None
    assert event.actor_label
    assert "password" not in event.context
    assert event.context["safe"] == "ok"


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_audit_event_cannot_be_modified_or_deleted():
    event = record_event(
        actor=None,
        action="test.action",
        resource="Resource",
        resource_identifier="1",
    )

    with pytest.raises(RuntimeError):
        event.delete()

    with pytest.raises(RuntimeError):
        event.action = "changed"
        event.save()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_denied_operation_can_be_audited():
    actor = UserFactory()
    target = UserFactory()
    role = RoleFactory(permissions=[PermissionFactory(codename="role_assign")])

    with pytest.raises(PermissionDenied):
        assign_role(actor=actor, user=target, role=role)

    denied_event = record_event(
        actor=actor,
        action="identity.role_assignment.denied",
        resource="RoleAssignment",
        context={"reason": "missing_permission"},
    )
    assert denied_event.action.endswith("denied")
