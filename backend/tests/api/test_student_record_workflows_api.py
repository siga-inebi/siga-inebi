import pytest
from django.test import Client
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.enrolments.models import Enrolment
from apps.people.models import Person
from apps.students import services
from apps.students.models import Guardian, StudentGuardianRelation
from tests.factories.academic import SectionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import GuardianFactory, StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def grant(user, student, *codes):
    role = RoleFactory(permissions=[PermissionFactory(codename=code) for code in codes])
    ScopeGrantFactory(assignment=RoleAssignmentFactory(user=user, role=role), student=student)


def url(student, name="student-record-status"):
    return reverse(name, kwargs={"public_id": student.public_id})


def person():
    return {
        "first_name": "Responsable",
        "last_name": "Sintetico",
        "cui": "9876543210123",
        "birth_date": "1990-01-01",
        "sex": "female",
        "nationality": "Guatemalteca",
        "address": "Direccion de prueba",
        "department": "Guatemala",
        "municipality": "Guatemala",
        "phone_number": "55500001",
        "email": "guardian@example.invalid",
    }


def post(client, target, payload):
    return client.post(target, payload, content_type="application/json")


def test_create_and_link_is_atomic_audited_and_private(auth_client):
    student = StudentFactory(status="active")
    grant(auth_client.user, student, "student_edit_basic", "student_view_basic")
    response = post(
        auth_client,
        url(student, "student-record-guardian-link"),
        {
            "person": person(),
            "relationship_label": "Madre",
        },
    )
    assert response.status_code == 201
    relation = StudentGuardianRelation.objects.get(pk=response.json()["id"])
    assert relation.student == student and relation.is_primary and relation.ends_at is None
    assert relation.guardian.person.cui == person()["cui"]
    assert "cui" not in response.json()["guardian_detail"]["person"]
    assert "birth_date" not in response.json()["guardian_detail"]["person"]
    assert AuditEvent.objects.filter(action="students.guardian.created").count() == 1
    assert (
        AuditEvent.objects.filter(action="students.student_guardian_relation.created").count() == 1
    )
    # Retrying the same creation cannot create a second person or relation.
    assert (
        post(
            auth_client,
            url(student, "student-record-guardian-link"),
            {
                "person": person(),
                "relationship_label": "Madre",
            },
        ).status_code
        == 400
    )
    assert StudentGuardianRelation.objects.count() == 1


def test_existing_guardian_links_without_duplicate_and_rejects_inactive(auth_client):
    student, guardian = StudentFactory(status="active"), GuardianFactory()
    grant(auth_client.user, student, "student_edit_basic")
    target = url(student, "student-record-guardian-link")
    payload = {"guardian_id": guardian.pk, "relationship_label": "Tutor"}
    assert post(auth_client, target, payload).status_code == 201
    assert post(auth_client, target, payload).status_code == 400
    guardian.is_active = False
    guardian.save()
    assert post(auth_client, target, payload).status_code == 400
    assert StudentGuardianRelation.objects.count() == 1


def test_create_link_rolls_back_person_guardian_relation_and_audits(auth_client, monkeypatch):
    student = StudentFactory(status="active")
    grant(auth_client.user, student, "student_edit_basic")
    before = (Person.objects.count(), Guardian.objects.count(), AuditEvent.objects.count())
    original = services.record_event

    def fail(**kwargs):
        if kwargs["action"] == "students.student_guardian_relation.created":
            raise RuntimeError("audit unavailable")
        return original(**kwargs)

    monkeypatch.setattr(services, "record_event", fail)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        post(
            auth_client,
            url(student, "student-record-guardian-link"),
            {
                "person": person(),
                "relationship_label": "Tutor",
            },
        )
    assert (Person.objects.count(), Guardian.objects.count(), AuditEvent.objects.count()) == before
    assert not StudentGuardianRelation.objects.exists()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"relationship_label": "Tutor"},
        {"guardian_id": 1, "person": person(), "relationship_label": "Tutor"},
        {"person": {"first_name": "Demo", "last_name": "Demo"}, "relationship_label": "Tutor"},
        {"guardian_id": 999999, "relationship_label": "Tutor", "student": 1},
    ],
)
def test_link_invalid_payload_has_no_writes(auth_client, payload):
    student = StudentFactory(status="active")
    grant(auth_client.user, student, "student_edit_basic")
    response = post(auth_client, url(student, "student-record-guardian-link"), payload)
    assert response.status_code == 400
    assert not Guardian.objects.exists() and not StudentGuardianRelation.objects.exists()


@pytest.mark.parametrize(
    "name,payload",
    [
        ("student-record-guardian-link", {"person": person(), "relationship_label": "Tutor"}),
        ("student-record-status", {"status": "withdrawn", "expected_status": "active"}),
    ],
)
def test_workflow_writes_require_session_permission_and_scope(auth_client, name, payload):
    student, other = StudentFactory.create_batch(2, status="active")
    target = url(student, name)
    assert post(Client(), target, payload).status_code == 403
    grant(auth_client.user, student, "student_view_basic")
    assert post(auth_client, target, payload).status_code == 403
    grant(auth_client.user, other, "student_edit_basic")
    assert post(auth_client, target, payload).status_code == 404
    student.refresh_from_db()
    assert student.status == "active" and not Guardian.objects.exists()


def test_status_readonly_scope_capability_and_no_false_denial(auth_client):
    student, other = StudentFactory.create_batch(2)
    grant(auth_client.user, student, "student_view_basic")
    response = auth_client.get(url(student))
    assert response.status_code == 200
    assert response.json()["can_change"] is False
    assert response.json()["last_change"] is None
    assert auth_client.get(url(other)).status_code == 404
    assert not AuditEvent.objects.filter(action="identity.authorization.denied").exists()


@pytest.mark.parametrize(
    "target,has_enrolment",
    [
        ("active", False),
        ("withdrawn", True),
        ("inactive", True),
    ],
)
def test_status_warnings_do_not_block_or_change_academic_history(
    auth_client, target, has_enrolment
):
    student = StudentFactory(status="pre_enrolled")
    grant(auth_client.user, student, "student_view_basic", "student_edit_basic")
    enrolment = None
    if has_enrolment:
        section = SectionFactory()
        enrolment = Enrolment.objects.create(
            student=student,
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
        )
    preview = auth_client.get(url(student), {"status": target})
    assert preview.status_code == 200 and preview.json()["warnings"]
    assert not AuditEvent.objects.filter(action="students.student.status_changed").exists()
    response = post(
        auth_client, url(student), {"status": target, "expected_status": student.status}
    )
    assert response.status_code == 200 and response.json()["warnings"]
    student.refresh_from_db()
    assert student.status == target and student.is_active
    if enrolment:
        enrolment.refresh_from_db()
        assert enrolment.status == "active" and enrolment.is_active
    event = AuditEvent.objects.get(action="students.student.status_changed")
    assert event.actor == auth_client.user
    assert event.context["before"] == {"status": "pre_enrolled"}
    assert event.context["after"] == {"status": target}
    trace = auth_client.get(url(student)).json()["last_change"]
    assert trace["actor_label"] == auth_client.user.username and trace["changed_at"]
    assert trace["previous_status"] == "pre_enrolled" and trace["status"] == target


def test_status_rejects_stale_same_invalid_and_inactive_without_reactivation(auth_client):
    student = StudentFactory(status="active")
    grant(auth_client.user, student, "student_edit_basic")
    for payload in [
        {"status": "invalid", "expected_status": "active"},
        {"status": "active", "expected_status": "active"},
        {"status": "withdrawn", "expected_status": "pre_enrolled"},
        {"status": "withdrawn", "expected_status": "active", "is_active": True},
    ]:
        assert post(auth_client, url(student), payload).status_code == 400
    student.is_active = False
    student.save()
    assert (
        post(
            auth_client, url(student), {"status": "withdrawn", "expected_status": "active"}
        ).status_code
        == 400
    )
    student.refresh_from_db()
    assert student.status == "active" and not student.is_active
    assert not AuditEvent.objects.filter(action="students.student.status_changed").exists()


def test_status_write_and_audit_rollback_together(auth_client, monkeypatch):
    student = StudentFactory(status="active")
    grant(auth_client.user, student, "student_edit_basic")

    def fail(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(services, "record_event", fail)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        post(auth_client, url(student), {"status": "withdrawn", "expected_status": "active"})
    student.refresh_from_db()
    assert student.status == "active"


def test_status_trace_preserves_legacy_events_and_ignores_other_student(auth_client):
    student, other = StudentFactory.create_batch(2, status="active")
    grant(auth_client.user, student, "student_view_basic")
    services.update_student(student=student, actor=auth_client.user, status="withdrawn")
    services.update_student(student=other, actor=auth_client.user, status="graduated")
    # Old general editors sent status even when it was unchanged. Keep their
    # audit events, but do not present those writes as a new state transition.
    services.update_student(student=student, actor=auth_client.user, status="withdrawn")
    result = auth_client.get(url(student)).json()
    assert result["last_change"]["status"] == "withdrawn"
    assert result["last_change"]["previous_status"] == "active"


def test_cui_uniqueness_guard_also_handles_database_race(auth_client):
    from apps.common.exceptions import DomainError

    existing = GuardianFactory()
    existing.person.cui = person()["cui"]
    existing.person.save()
    student = StudentFactory(status="active")
    before = Person.objects.count()
    with pytest.raises(DomainError, match="CUI"):
        services.link_guardian_from_record(
            student=student, person=person(), relationship_label="Tutor", actor=auth_client.user
        )
    assert Person.objects.count() == before
    assert not StudentGuardianRelation.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_status_confirmations_cannot_overwrite_each_other(auth_client):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    from apps.common.exceptions import DomainError

    student = StudentFactory(status="active")
    barrier = Barrier(2)

    def change(target):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            services.change_student_record_status(
                student=student, actor=auth_client.user, status=target, expected_status="active"
            )
            return "changed"
        except DomainError:
            return "stale"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(change, ["withdrawn", "graduated"]))
    assert sorted(results) == ["changed", "stale"]
    assert AuditEvent.objects.filter(action="students.student.status_changed").count() == 1
