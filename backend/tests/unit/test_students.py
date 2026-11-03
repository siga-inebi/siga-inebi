import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.students.services import deactivate_student, guardian_can_access_student
from tests.factories.identity import UserFactory
from tests.factories.students import (
    EmergencyContactFactory,
    GuardianFactory,
    StudentFactory,
    StudentGuardianRelationFactory,
    StudentHealthNoteFactory,
    StudentObservationFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
def test_student_code_unique():
    student = StudentFactory(student_code="STU-0001")

    with pytest.raises(IntegrityError):
        StudentFactory(student_code=student.student_code)


@pytest.mark.unit
@pytest.mark.django_db
def test_deactivate_student_preserves_record():
    student = StudentFactory(status="active", is_active=True)

    deactivate_student(student=student)
    student.refresh_from_db()

    assert student.is_active is False
    assert student.status == student.StudentStatus.INACTIVE


@pytest.mark.unit
@pytest.mark.django_db
def test_guardian_access_cut_off_after_relation_end():
    guardian = GuardianFactory()
    user = UserFactory(person=guardian.person)
    student = StudentFactory()
    relation = StudentGuardianRelationFactory(guardian=guardian, student=student)
    relation.ends_at = timezone.localdate()
    relation.save(update_fields=["ends_at", "updated_at"])

    assert guardian_can_access_student(user=user, student=student, when=relation.starts_at) is False


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory",
    [
        StudentFactory,
        GuardianFactory,
        StudentGuardianRelationFactory,
        EmergencyContactFactory,
        StudentHealthNoteFactory,
        StudentObservationFactory,
    ],
)
def test_student_record_instance_cannot_be_physically_deleted(factory):
    record = factory()

    with pytest.raises(RuntimeError, match="cannot be physically deleted"):
        record.delete()

    assert record.__class__.objects.filter(pk=record.pk).exists()


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory",
    [
        StudentFactory,
        GuardianFactory,
        StudentGuardianRelationFactory,
        EmergencyContactFactory,
        StudentHealthNoteFactory,
        StudentObservationFactory,
    ],
)
def test_student_record_queryset_cannot_be_physically_deleted(factory):
    record = factory()

    with pytest.raises(RuntimeError, match="cannot be physically deleted"):
        record.__class__.objects.filter(pk=record.pk).delete()

    assert record.__class__.objects.filter(pk=record.pk).exists()
