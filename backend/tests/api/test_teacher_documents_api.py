"""RF-DOC-001: REST contract of the teacher's document dossier."""

import hashlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.documents.models import DocumentRecord
from tests.factories.documents import DocumentRecordFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.students import StudentFactory
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

MISSING_UUID = "00000000-0000-0000-0000-000000000000"
PAYLOAD = b"%PDF-1.4 titulo profesional"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _login(client, *codenames, person=None, **scope):
    user = UserFactory(person=person) if person is not None else UserFactory()
    permissions = [PermissionFactory(codename=codename) for codename in codenames]
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=permissions))
    if scope:
        ScopeGrantFactory(assignment=assignment, **scope)
    client.force_login(user)
    return user


def _records_url(teacher_id):
    return reverse("teacher-document-record-list-create", args=[teacher_id])


def _upload(client, teacher, payload=PAYLOAD):
    return client.post(
        _records_url(teacher.public_id),
        {"file": SimpleUploadedFile("titulo.pdf", payload, content_type="application/pdf")},
    )


@pytest.mark.security
@pytest.mark.parametrize(
    ("method", "url_name", "kwargs"),
    [
        ("get", "teacher-document-record-list-create", {"teacher_id": MISSING_UUID}),
        ("post", "teacher-document-record-list-create", {"teacher_id": MISSING_UUID}),
        ("post", "document-record-download-token", {"public_id": MISSING_UUID}),
    ],
)
def test_teacher_document_endpoints_require_authentication(client, method, url_name, kwargs):
    """RF-DOC-001: no anonymous access to a teacher dossier."""
    response = getattr(client, method)(reverse(url_name, kwargs=kwargs))

    assert response.status_code in (401, 403)


def test_staff_uploads_and_lists_teacher_documents(client):
    """RF-DOC-001: the upload is linked to the teacher and listed in the dossier."""
    teacher = TeacherFactory()
    _login(client, "document_upload", "document_read", module_key="teachers")

    created = _upload(client, teacher)

    assert created.status_code == 201
    body = created.json()
    assert body["teacher_id"] == str(teacher.public_id)
    assert body["student_id"] is None
    assert body["enrolment_id"] is None
    assert body["checksum"] == hashlib.sha256(PAYLOAD).hexdigest()
    assert body["version_number"] == 1

    listed = client.get(_records_url(teacher.public_id))

    assert listed.status_code == 200
    assert [item["public_id"] for item in listed.json()["results"]] == [body["public_id"]]


def test_teacher_lists_own_dossier(client):
    """RF-DOC-001: a teacher with document.read sees their own documents."""
    teacher = TeacherFactory()
    record = DocumentRecordFactory(student=None, teacher=teacher)
    DocumentRecordFactory(student=None, teacher=TeacherFactory())
    _login(client, "document_read", person=teacher.person)

    response = client.get(_records_url(teacher.public_id))

    assert response.status_code == 200
    assert [item["public_id"] for item in response.json()["results"]] == [str(record.public_id)]


@pytest.mark.security
def test_teacher_cannot_list_another_teachers_dossier(client):
    """RF-DOC-001: out-of-scope dossier answers 403 and is audited."""
    _login(client, "document_read", person=TeacherFactory().person)

    response = client.get(_records_url(TeacherFactory().public_id))

    assert response.status_code == 403
    assert AuditEvent.objects.filter(action="documents.document.read_denied").exists()


@pytest.mark.security
def test_listing_without_read_permission_is_forbidden(client):
    """RF-DOC-001: scope without the atomic permission is denied."""
    _login(client, "document_upload", module_key="teachers")

    response = client.get(_records_url(TeacherFactory().public_id))

    assert response.status_code == 403


@pytest.mark.security
def test_upload_without_permission_is_forbidden(client):
    """RF-DOC-001: document.upload is required to load a teacher document."""
    teacher = TeacherFactory()
    _login(client, "document_read", module_key="teachers")

    response = _upload(client, teacher)

    assert response.status_code == 403
    assert not DocumentRecord.objects.filter(teacher=teacher).exists()


@pytest.mark.security
def test_upload_with_student_scope_only_is_forbidden(client):
    """RF-DOC-001: the students module scope does not reach teacher dossiers."""
    teacher = TeacherFactory()
    _login(client, "document_upload", module_key="students")

    response = _upload(client, teacher)

    assert response.status_code == 403


def test_unknown_teacher_returns_404(client):
    """RF-DOC-001: unknown teacher ids answer 404."""
    _login(client, "document_read", "document_upload", module_key="teachers")

    assert client.get(_records_url(MISSING_UUID)).status_code == 404


def test_teacher_document_version_download_and_integrity_flow(client):
    """RF-DOC-001 / RF-DOC-005: version, token download and SHA-256 check for teachers."""
    teacher = TeacherFactory()
    _login(client, "document_upload", "document_read", module_key="teachers")
    original = _upload(client, teacher).json()

    replaced = client.post(
        reverse("document-record-version-create", args=[original["public_id"]]),
        {
            "file": SimpleUploadedFile(
                "titulo-v2.pdf", b"%PDF-1.4 v2", content_type="application/pdf"
            )
        },
    )
    assert replaced.status_code == 201
    replacement = replaced.json()
    assert replacement["version_number"] == 2
    assert replacement["supersedes_id"] == original["public_id"]
    assert replacement["teacher_id"] == str(teacher.public_id)

    issued = client.post(reverse("document-record-download-token", args=[replacement["public_id"]]))
    assert issued.status_code == 201
    downloaded = client.get(issued.json()["download_url"])
    assert downloaded.status_code == 200
    assert hashlib.sha256(downloaded.content).hexdigest() == replacement["checksum"]

    verified = client.post(
        reverse("document-record-integrity-verify", args=[replacement["public_id"]])
    )
    assert verified.status_code == 204


def test_download_token_endpoint_serves_student_documents_too(client):
    """RF-DOC-005: the token endpoint applies the student scope rules unchanged."""
    student = StudentFactory()
    _login(client, "document_read", "document_upload", student=student)
    created = client.post(
        reverse("document-record-upload"),
        {
            "student_id": str(student.public_id),
            "file": SimpleUploadedFile("acta.pdf", PAYLOAD, content_type="application/pdf"),
        },
    )
    assert created.status_code == 201

    issued = client.post(
        reverse("document-record-download-token", args=[created.json()["public_id"]])
    )

    assert issued.status_code == 201
    assert client.get(issued.json()["download_url"]).content == PAYLOAD


@pytest.mark.security
def test_download_token_out_of_scope_is_forbidden(client):
    """RF-DOC-005: no token is issued for a dossier outside the caller's scope."""
    record = DocumentRecordFactory(student=None, teacher=TeacherFactory())
    _login(client, "document_read", person=TeacherFactory().person)

    response = client.post(reverse("document-record-download-token", args=[record.public_id]))

    assert response.status_code == 403
