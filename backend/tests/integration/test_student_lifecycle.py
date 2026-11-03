import pytest

from apps.students.models import Student
from apps.students.services import deactivate_student, update_student
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory, StudentGuardianRelationFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_student_lifecycle_preserves_profile_and_relations():
    actor = UserFactory()
    student = StudentFactory(status=Student.StudentStatus.PRE_ENROLLED)
    relation = StudentGuardianRelationFactory(student=student)

    update_student(student=student, status=Student.StudentStatus.ACTIVE, actor=actor)
    deactivate_student(student=student, actor=actor)

    student.refresh_from_db()
    relation.refresh_from_db()
    assert student.status == Student.StudentStatus.INACTIVE
    assert student.is_active is False
    assert student.person_id is not None
    assert relation.student_id == student.pk
