"""
RF-ARC-002 — compresion y normalizacion de imagenes adjuntas.

Contrato por API de los dos puntos de carga que reciben imagenes JPEG/PNG:
el respaldo de una justificacion de asistencia (RF-JUS-007) y el expediente
documental del estudiante. En ambos el binario guardado es la imagen
normalizada y el checksum/tamano registrados corresponden a ese binario.
"""

import hashlib
from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.attendance.models import Justification
from apps.documents.models import DocumentRecord
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.images import GPS_IFD_TAG, photo_upload
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.IMAGE_UPLOAD_MAX_DIMENSION_PX = 1024
    return tmp_path


def _grant(user, student, *codenames):
    permissions = [PermissionFactory(codename=codename) for codename in codenames]
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=permissions))
    ScopeGrantFactory(assignment=assignment, student=student)


def _submit_justification(client, student):
    _grant(client.user, student, "attendance_justification_request")
    response = client.post(
        reverse("attendance-justification-submit"),
        {
            "student_id": str(student.public_id),
            "absence_date": str(timezone.localdate() - timedelta(days=1)),
            "reason": "Cita medica",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    return Justification.objects.get(public_id=response.json()["public_id"])


def _read_stored(storage_key):
    with default_storage.open(storage_key, "rb") as stored_file:
        return stored_file.read()


def test_justification_attachment_upload_stores_a_normalized_image(auth_client, media_root):
    """
    RF-ARC-002: GIVEN un encargado que sube como justificante una foto grande
    tomada con el telefono (EXIF de orientacion y GPS), WHEN la adjunta por API,
    THEN se guarda reducida, recomprimida, derecha y sin metadatos, y la
    respuesta informa el tamano y el checksum del binario final almacenado.
    """
    upload = photo_upload(size=(4000, 3000), orientation=6, with_gps=True)
    original_size = upload.size
    justification = _submit_justification(auth_client, StudentFactory())

    response = auth_client.post(
        reverse("attendance-justification-attachment", args=[justification.public_id]),
        {"file": upload},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == "image/jpeg"
    justification.refresh_from_db()
    stored = _read_stored(justification.attachment.storage_key)
    assert body["size_bytes"] == len(stored) < original_size
    assert body["checksum"] == hashlib.sha256(stored).hexdigest()
    with Image.open(BytesIO(stored)) as image:
        assert image.format == "JPEG"
        assert image.size == (768, 1024)
        assert dict(image.getexif()) == {}


def test_justification_attachment_upload_rejects_a_corrupt_image(auth_client, media_root):
    """RF-ARC-002: una imagen danada se rechaza con 400, mensaje en espanol y sin adjunto."""
    justification = _submit_justification(auth_client, StudentFactory())
    corrupt = SimpleUploadedFile("foto.jpg", b"\xff\xd8\xff no es jpeg", content_type="image/jpeg")

    response = auth_client.post(
        reverse("attendance-justification-attachment", args=[justification.public_id]),
        {"file": corrupt},
    )

    assert response.status_code == 400
    assert "La imagen adjunta esta danada" in str(response.json())
    justification.refresh_from_db()
    assert not hasattr(justification, "attachment")
    assert not any(media_root.rglob("*.jpg"))


def test_document_image_upload_is_normalized_and_passes_integrity_verification(client, media_root):
    """
    RF-ARC-002 + RF-ARC-003: una imagen subida al expediente se guarda
    normalizada (sin GPS) y la verificacion de integridad SHA-256 sigue
    aprobando porque el checksum se calcula sobre el binario almacenado.
    """
    user = UserFactory()
    student = StudentFactory()
    _grant(user, student, "document_upload", "document_read")
    client.force_login(user)

    response = client.post(
        reverse("document-record-upload"),
        {
            "student_id": str(student.public_id),
            "file": photo_upload("partida.png", size=(3000, 2000), with_gps=True),
        },
        format="multipart",
    )

    assert response.status_code == 201
    record = DocumentRecord.objects.get(public_id=response.json()["public_id"])
    stored = _read_stored(record.storage_key)
    assert record.content_type == "image/png"
    assert record.size_bytes == len(stored)
    assert record.checksum == hashlib.sha256(stored).hexdigest()
    with Image.open(BytesIO(stored)) as image:
        assert image.format == "PNG"
        assert image.size == (1024, 683)
        assert not image.getexif().get_ifd(GPS_IFD_TAG)

    verify = client.post(reverse("document-record-integrity-verify", args=[record.public_id]))

    assert verify.status_code == 204
