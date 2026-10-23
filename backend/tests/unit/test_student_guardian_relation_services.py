import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.common.models import DomainError
from apps.students.models import StudentGuardianRelation
from apps.students.services import (
    change_primary_student_guardian_relation,
    create_student_guardian_relation,
    end_student_guardian_relation,
    update_student_guardian_relation,
)
from tests.factories.students import GuardianFactory, StudentFactory


@pytest.mark.unit
@pytest.mark.django_db
def test_first_current_guardian_relationship_is_primary():
    relation = create_student_guardian_relation(
        student=StudentFactory(),
        guardian=GuardianFactory(),
        relationship_label="Madre",
    )

    assert relation.is_primary is True


@pytest.mark.unit
@pytest.mark.django_db
def test_database_allows_at_most_one_current_primary_relationship():
    student = StudentFactory()
    create_student_guardian_relation(
        student=student,
        guardian=GuardianFactory(),
        relationship_label="Madre",
    )

    with transaction.atomic(), pytest.raises(IntegrityError):
        StudentGuardianRelation.objects.create(
            student=student,
            guardian=GuardianFactory(),
            relationship_label="Padre",
            is_primary=True,
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_ending_primary_relationship_without_replacement_leaves_no_primary():
    relation = create_student_guardian_relation(
        student=StudentFactory(),
        guardian=GuardianFactory(),
        relationship_label="Madre",
    )

    end_student_guardian_relation(relation=relation)

    relation.refresh_from_db()
    assert relation.ends_at == timezone.localdate()
    assert relation.is_primary is False
    assert not StudentGuardianRelation.objects.filter(
        student=relation.student, is_primary=True, ends_at__isnull=True
    ).exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_replacing_and_ending_primary_preserves_other_relationships():
    student = StudentFactory()
    primary = create_student_guardian_relation(
        student=student,
        guardian=GuardianFactory(),
        relationship_label="Madre",
    )
    replacement = create_student_guardian_relation(
        student=student,
        guardian=GuardianFactory(),
        relationship_label="Padre",
    )
    other_student_relation = create_student_guardian_relation(
        student=StudentFactory(),
        guardian=primary.guardian,
        relationship_label="Madre",
    )

    end_student_guardian_relation(relation=primary, replacement_relation=replacement)

    primary.refresh_from_db()
    replacement.refresh_from_db()
    other_student_relation.refresh_from_db()
    assert primary.ends_at is not None
    assert primary.is_primary is False
    assert replacement.ends_at is None
    assert replacement.is_primary is True
    assert other_student_relation.ends_at is None
    assert other_student_relation.is_primary is True


@pytest.mark.unit
@pytest.mark.django_db
def test_change_primary_replaces_the_current_primary():
    student = StudentFactory()
    first = create_student_guardian_relation(
        student=student,
        guardian=GuardianFactory(),
        relationship_label="Madre",
    )
    second = create_student_guardian_relation(
        student=student,
        guardian=GuardianFactory(),
        relationship_label="Padre",
    )

    change_primary_student_guardian_relation(relation=second)

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_primary is False
    assert second.is_primary is True


@pytest.mark.unit
@pytest.mark.django_db
def test_relation_edit_rolls_back_when_audit_fails(monkeypatch):
    relation = create_student_guardian_relation(
        student=StudentFactory(),
        guardian=GuardianFactory(),
        relationship_label="Madre",
    )

    def fail(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("apps.students.services.record_event", fail)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        update_student_guardian_relation(relation=relation, relationship_label="Tutor")
    relation.refresh_from_db()
    assert relation.relationship_label == "Madre"


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.parametrize("label", [" ", "x" * 101])
def test_relation_edit_validates_description_in_domain(label):
    relation = create_student_guardian_relation(
        student=StudentFactory(),
        guardian=GuardianFactory(),
        relationship_label="Madre",
    )
    with pytest.raises(DomainError):
        update_student_guardian_relation(relation=relation, relationship_label=label)
