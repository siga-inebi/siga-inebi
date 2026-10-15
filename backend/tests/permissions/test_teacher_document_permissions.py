"""RF-DOC-001 / RF-DOC-004: who may read or upload a teacher's dossier."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditEvent
from apps.common.exceptions import AuthorizationError
from apps.documents.services import (
    ensure_teacher_document_access,
    issue_document_download_token,
    upload_teacher_document_record,
)
from tests.factories.academic import InstitutionFactory
from tests.factories.documents import DocumentRecordFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.permissions, pytest.mark.django_db]


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _user(*codenames, person=None, **scope):
    user = UserFactory(person=person) if person is not None else UserFactory()
    permissions = [PermissionFactory(codename=codename) for codename in codenames]
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=permissions))
    if scope:
        ScopeGrantFactory(assignment=assignment, **scope)
    return user


def _pdf():
    return SimpleUploadedFile("contrato.pdf", b"%PDF-1.4 contrato", content_type="application/pdf")


def test_teacher_with_read_permission_sees_own_dossier():
    """RF-DOC-001: a teacher sees their own documents without an extra grant."""
    teacher = TeacherFactory()
    user = _user("document_read", person=teacher.person)

    assert ensure_teacher_document_access(actor=user, teacher=teacher) is True
    event = AuditEvent.objects.filter(action="documents.document.read").latest("pk")
    assert event.context["scope"] == "own"


def test_teacher_cannot_read_another_teachers_dossier():
    """RF-DOC-001: deny by default; being a teacher does not open other dossiers."""
    own = TeacherFactory()
    other = TeacherFactory()
    user = _user("document_read", person=own.person)

    with pytest.raises(AuthorizationError):
        ensure_teacher_document_access(actor=user, teacher=other)
    denied = AuditEvent.objects.filter(action="documents.document.read_denied").latest("pk")
    assert denied.context["reason"] == "missing_scope"


def test_teacher_without_read_permission_cannot_read_own_dossier():
    """RF-DOC-001: the atomic permission is required even for one's own dossier."""
    teacher = TeacherFactory()
    user = _user("student_view_basic", person=teacher.person)

    with pytest.raises(AuthorizationError):
        ensure_teacher_document_access(actor=user, teacher=teacher)
    denied = AuditEvent.objects.filter(action="documents.document.read_denied").latest("pk")
    assert denied.context["reason"] == "missing_permission"


def test_administrative_staff_with_teachers_module_scope_reads_any_teacher():
    """RF-DOC-001: the administrative scope over teachers is the module scope."""
    user = _user("document_read", module_key="teachers")

    assert ensure_teacher_document_access(actor=user, teacher=TeacherFactory()) is True


def test_student_scopes_do_not_reach_teacher_dossiers():
    """RF-DOC-001: an institution or students-module grant does not cover teachers."""
    institution_user = _user("document_read", institution=InstitutionFactory())
    students_user = _user("document_read", module_key="students")

    for user in (institution_user, students_user):
        with pytest.raises(AuthorizationError):
            ensure_teacher_document_access(actor=user, teacher=TeacherFactory())


def test_upload_requires_upload_permission_with_teachers_module_scope():
    """RF-DOC-001: secretary/administrator load documents into a teacher dossier."""
    teacher = TeacherFactory()
    allowed = _user("document_upload", module_key="teachers")
    read_only = _user("document_read", module_key="teachers")
    wrong_scope = _user("document_upload", module_key="students")

    record = upload_teacher_document_record(actor=allowed, teacher=teacher, upload=_pdf())
    assert record.teacher_id == teacher.pk

    for user in (read_only, wrong_scope):
        with pytest.raises(AuthorizationError):
            upload_teacher_document_record(actor=user, teacher=teacher, upload=_pdf())
    assert AuditEvent.objects.filter(action="documents.document.upload_denied").count() == 2


def test_teacher_cannot_upload_into_own_dossier():
    """RF-DOC-001: the teacher reads their dossier; staff maintain it."""
    teacher = TeacherFactory()
    user = _user("document_read", "document_upload", person=teacher.person)

    with pytest.raises(AuthorizationError):
        upload_teacher_document_record(actor=user, teacher=teacher, upload=_pdf())


def test_download_token_for_teacher_document_follows_teacher_rules():
    """RF-DOC-001 / RF-DOC-005: token issuance reuses the teacher access guard."""
    teacher = TeacherFactory()
    record = DocumentRecordFactory(student=None, teacher=teacher)
    owner = _user("document_read", person=teacher.person)
    stranger = _user("document_read", module_key="students")

    token = issue_document_download_token(actor=owner, document=record)
    assert token.token
    with pytest.raises(AuthorizationError):
        issue_document_download_token(actor=stranger, document=record)
