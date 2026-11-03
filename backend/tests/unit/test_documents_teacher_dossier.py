"""RF-DOC-001: documents linked to the teacher's institutional dossier (services)."""

import hashlib

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction

from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.documents.models import DocumentRecord
from apps.documents.services import (
    replace_document_record,
    upload_teacher_document_record,
    verify_document_storage_integrity,
    verify_stored_document_checksum,
)
from tests.factories.documents import DocumentRecordFactory
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _pdf(name="titulo.pdf", payload=b"%PDF-1.4 titulo docente"):
    return SimpleUploadedFile(name, payload, content_type="application/pdf")


def test_upload_teacher_document_links_record_to_teacher_with_sha256_outside_db():
    """RF-DOC-001: the upload lands in the teacher's dossier, never in a student's."""
    actor = UserFactory(is_superuser=True)
    teacher = TeacherFactory()
    payload = b"%PDF-1.4 titulo docente"

    record = upload_teacher_document_record(actor=actor, teacher=teacher, upload=_pdf())

    assert record.teacher_id == teacher.pk
    assert record.student_id is None
    assert record.owner == teacher
    assert record.checksum == hashlib.sha256(payload).hexdigest()
    assert record.version_number == 1
    assert record.storage_key.startswith(f"documents/teachers/{teacher.public_id}/")
    with default_storage.open(record.storage_key, "rb") as stored:
        assert stored.read() == payload
    assert AuditEvent.objects.filter(
        action="documents.document.uploaded", resource_identifier=str(record.pk)
    ).exists()


def test_upload_teacher_document_requires_a_teacher():
    """RF-DOC-001: a teacher upload without a teacher is rejected."""
    with pytest.raises(DomainError):
        upload_teacher_document_record(
            actor=UserFactory(is_superuser=True), teacher=None, upload=_pdf()
        )


def test_upload_teacher_document_rejects_unsupported_type():
    """RF-DOC-001: the teacher pipeline keeps the storage catalogue of types."""
    with pytest.raises(DomainError):
        upload_teacher_document_record(
            actor=UserFactory(is_superuser=True),
            teacher=TeacherFactory(),
            upload=SimpleUploadedFile("macro.docm", b"x", content_type="application/pdf"),
        )


def test_replacing_a_teacher_document_keeps_the_immutable_history():
    """RF-DOC-001: versioning works the same for teachers as for students."""
    actor = UserFactory(is_superuser=True)
    teacher = TeacherFactory()
    original = upload_teacher_document_record(actor=actor, teacher=teacher, upload=_pdf())

    replacement = replace_document_record(
        actor=actor, record=original, upload=_pdf(payload=b"%PDF-1.4 v2")
    )

    original.refresh_from_db()
    assert replacement.teacher_id == teacher.pk
    assert replacement.student_id is None
    assert replacement.version_group_id == original.version_group_id
    assert replacement.version_number == 2
    assert replacement.supersedes_id == original.pk
    assert original.is_active is False
    assert original.status == DocumentRecord.StorageStatus.ARCHIVED
    assert DocumentRecord.objects.filter(teacher=teacher).count() == 2


def test_document_record_must_have_exactly_one_owner():
    """RF-DOC-001: the database refuses a record with both owners or none."""
    student = StudentFactory()
    teacher = TeacherFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        DocumentRecordFactory(student=student, teacher=teacher)
    with pytest.raises(IntegrityError), transaction.atomic():
        DocumentRecordFactory(student=None, teacher=None)


def test_teacher_owner_of_a_record_is_immutable():
    """RF-DOC-001: moving a record to another dossier would rewrite history."""
    record = DocumentRecordFactory(student=None, teacher=TeacherFactory())
    record.teacher = TeacherFactory()

    with pytest.raises(RuntimeError):
        record.save()


def test_stored_checksum_verification_works_for_teacher_documents():
    """RF-DOC-001: the SHA-256 integrity check covers teacher documents."""
    actor = UserFactory(is_superuser=True)
    record = upload_teacher_document_record(actor=actor, teacher=TeacherFactory(), upload=_pdf())

    assert verify_stored_document_checksum(actor=actor, document=record) is True

    default_storage.delete(record.storage_key)
    default_storage.save(record.storage_key, ContentFile(b"tampered"))
    with pytest.raises(DomainError):
        verify_stored_document_checksum(actor=actor, document=record)


def test_storage_integrity_scan_reports_the_teacher_owner():
    """RF-DOC-001: the integrity scan no longer assumes every record has a student."""
    teacher = TeacherFactory()
    DocumentRecordFactory(student=None, teacher=teacher, storage_key="local/missing-teacher.pdf")

    result = verify_document_storage_integrity()

    issue = next(item for item in result["issues"] if item.get("teacher_id"))
    assert issue["teacher_id"] == str(teacher.public_id)
    assert issue["status"] == "missing"
