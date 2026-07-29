from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.students.services import deactivate_student, guardian_can_access_student
from tests.factories.identity import UserFactory
from tests.factories.students import GuardianFactory, StudentFactory, StudentGuardianRelationFactory


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

    assert guardian_can_access_student(user=user, student=student, when=relation.ends_at) is True
    assert (
        guardian_can_access_student(
            user=user,
            student=student,
            when=relation.ends_at + timedelta(days=1),
        )
        is False
    )
