import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.students.models import Student
from apps.students.services import student_allows_interaction, update_student
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_update_student_status_uses_domain_service_and_audits_change():
    actor = UserFactory()
    student = StudentFactory(status=Student.StudentStatus.ACTIVE)

    updated = update_student(
        student=student,
        status=Student.StudentStatus.GRADUATED,
        actor=actor,
    )

    assert updated.status == Student.StudentStatus.GRADUATED
    event = AuditEvent.objects.get(action="students.student.updated")
    assert event.actor == actor
    assert event.context["before"] == {"status": Student.StudentStatus.ACTIVE}
    assert event.context["after"] == {"status": Student.StudentStatus.GRADUATED}


def test_update_student_rejects_invalid_status_without_writing():
    student = StudentFactory(status=Student.StudentStatus.ACTIVE)

    with pytest.raises(DomainError, match="status is invalid"):
        update_student(student=student, status="unknown")

    student.refresh_from_db()
    assert student.status == Student.StudentStatus.ACTIVE


def test_update_student_rejects_non_image_photo_without_replacing_current_file():
    student = StudentFactory()
    original_name = student.photo.name
    document = SimpleUploadedFile("notes.txt", b"not-an-image", content_type="text/plain")

    with pytest.raises(DomainError, match="photo must be an image"):
        update_student(student=student, photo=document)

    student.refresh_from_db()
    assert student.photo.name == original_name


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (Student.StudentStatus.PRE_ENROLLED, False),
        (Student.StudentStatus.ACTIVE, True),
        (Student.StudentStatus.INACTIVE, False),
        (Student.StudentStatus.WITHDRAWN, False),
        (Student.StudentStatus.GRADUATED, False),
    ],
)
def test_only_active_status_allows_ordinary_interaction(status, expected):
    student = StudentFactory(status=status, is_active=True)

    assert student_allows_interaction(student) is expected


def test_soft_deleted_active_student_does_not_allow_interaction():
    student = StudentFactory(status=Student.StudentStatus.ACTIVE, is_active=False)

    assert student_allows_interaction(student) is False
