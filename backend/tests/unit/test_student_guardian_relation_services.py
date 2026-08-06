from datetime import timedelta

import pytest
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.students.services import (
    create_student_guardian_relation,
    end_student_guardian_relation,
    update_student_guardian_relation,
)
from tests.factories.identity import UserFactory
from tests.factories.students import GuardianFactory, StudentFactory, StudentGuardianRelationFactory


@pytest.mark.unit
@pytest.mark.django_db
def test_create_relation_persists_fields():
    student = StudentFactory()
    guardian = GuardianFactory()

    relation = create_student_guardian_relation(
        student=student, guardian=guardian, relationship_label="Madre", is_primary=True
    )

    relation.refresh_from_db()
    assert relation.student_id == student.pk
    assert relation.guardian_id == guardian.pk
    assert relation.relationship_label == "Madre"
    assert relation.is_primary is True
    assert relation.ends_at is None


@pytest.mark.unit
@pytest.mark.django_db
def test_create_relation_defaults_starts_at_to_today():
    student = StudentFactory()
    guardian = GuardianFactory()

    relation = create_student_guardian_relation(
        student=student, guardian=guardian, relationship_label="Madre"
    )

    assert relation.starts_at == timezone.localdate()


@pytest.mark.unit
@pytest.mark.django_db
def test_create_relation_records_audit_event():
    student = StudentFactory()
    guardian = GuardianFactory()
    actor = UserFactory()

    relation = create_student_guardian_relation(
        student=student, guardian=guardian, relationship_label="Madre", actor=actor
    )

    event = AuditEvent.objects.get(
        resource="StudentGuardianRelation", resource_identifier=str(relation.pk)
    )
    assert event.action == "students.student_guardian_relation.created"
    assert event.actor_id == actor.pk


@pytest.mark.unit
@pytest.mark.django_db
def test_create_relation_rejects_inactive_student():
    student = StudentFactory(is_active=False)
    guardian = GuardianFactory()

    with pytest.raises(DomainError):
        create_student_guardian_relation(
            student=student, guardian=guardian, relationship_label="Madre"
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_create_relation_rejects_inactive_guardian():
    student = StudentFactory()
    guardian = GuardianFactory(is_active=False)

    with pytest.raises(DomainError):
        create_student_guardian_relation(
            student=student, guardian=guardian, relationship_label="Madre"
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_create_relation_rejects_duplicate_active_pairing():
    existing = StudentGuardianRelationFactory()

    with pytest.raises(DomainError):
        create_student_guardian_relation(
            student=existing.student, guardian=existing.guardian, relationship_label="Tutor"
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_create_relation_allows_new_pairing_once_previous_one_ended():
    existing = StudentGuardianRelationFactory(ends_at=timezone.localdate())

    relation = create_student_guardian_relation(
        student=existing.student, guardian=existing.guardian, relationship_label="Tutor"
    )

    assert relation.pk != existing.pk


@pytest.mark.unit
@pytest.mark.django_db
def test_create_relation_promoting_primary_demotes_previous():
    student = StudentFactory()
    previous = StudentGuardianRelationFactory(student=student, is_primary=True)
    new_guardian = GuardianFactory()

    relation = create_student_guardian_relation(
        student=student, guardian=new_guardian, relationship_label="Padre", is_primary=True
    )

    previous.refresh_from_db()
    assert previous.is_primary is False
    assert relation.is_primary is True


@pytest.mark.unit
@pytest.mark.django_db
def test_update_relation_applies_only_supplied_fields():
    relation = StudentGuardianRelationFactory(relationship_label="Padre")

    update_student_guardian_relation(relation=relation, relationship_label="Tutor")

    relation.refresh_from_db()
    assert relation.relationship_label == "Tutor"


@pytest.mark.unit
@pytest.mark.django_db
def test_update_relation_promoting_primary_demotes_previous():
    student = StudentFactory()
    previous = StudentGuardianRelationFactory(student=student, is_primary=True)
    candidate = StudentGuardianRelationFactory(student=student, is_primary=False)

    update_student_guardian_relation(relation=candidate, is_primary=True)

    previous.refresh_from_db()
    candidate.refresh_from_db()
    assert previous.is_primary is False
    assert candidate.is_primary is True


@pytest.mark.unit
@pytest.mark.django_db
def test_update_relation_records_audit_event_with_changed_fields():
    relation = StudentGuardianRelationFactory()
    actor = UserFactory()

    update_student_guardian_relation(relation=relation, relationship_label="Tutor", actor=actor)

    event = AuditEvent.objects.get(
        resource="StudentGuardianRelation",
        resource_identifier=str(relation.pk),
        action="students.student_guardian_relation.updated",
    )
    assert event.actor_id == actor.pk
    assert event.context["fields"] == ["relationship_label"]


@pytest.mark.unit
@pytest.mark.django_db
def test_end_relation_sets_ends_at_to_today_by_default():
    relation = StudentGuardianRelationFactory(ends_at=None)

    end_student_guardian_relation(relation=relation)

    relation.refresh_from_db()
    assert relation.ends_at == timezone.localdate()


@pytest.mark.unit
@pytest.mark.django_db
def test_end_relation_rejects_ends_at_before_starts_at():
    relation = StudentGuardianRelationFactory(starts_at=timezone.localdate(), ends_at=None)

    with pytest.raises(DomainError):
        end_student_guardian_relation(
            relation=relation, ends_at=relation.starts_at - timedelta(days=1)
        )
