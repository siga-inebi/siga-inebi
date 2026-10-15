"""RF-EMI-001: emission -> download -> integrity verification, end to end over the API."""

import hashlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.documents.models import DocumentIssuance
from apps.enrolments.services import create_enrolment
from tests.factories.academic import SectionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.students import StudentFactory
from tests.pdf_assertions import assert_pdf_structurally_valid

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _secretary_for(student):
    user = UserFactory()
    permissions = [PermissionFactory(codename=code) for code in ("document_issue", "document_read")]
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=permissions))
    ScopeGrantFactory(assignment=assignment, student=student)
    return user


def _verify(client, issuance_id, payload):
    return client.post(
        reverse("document-issuance-integrity-verify", args=[issuance_id]),
        {"file": SimpleUploadedFile("emitido.pdf", payload, content_type="application/pdf")},
    )


def test_constancia_emission_download_and_integrity_verification(client):
    """RF-EMI-001: the downloaded constancia verifies; a tampered copy does not."""
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    client.force_login(_secretary_for(enrolment.student))

    # 1. Emission: the response body IS the download (RF-DOC-008: never stored).
    emitted = client.post(
        reverse("document-individual-issuance"),
        {"enrolment_id": str(enrolment.public_id), "document_type": "enrolment_certificate"},
        content_type="application/json",
    )
    assert emitted.status_code == 201
    pdf = emitted.content
    assert_pdf_structurally_valid(pdf)

    # 2. The register holds the hash of exactly those bytes.
    issuance = DocumentIssuance.objects.get(public_id=emitted["X-Document-Issuance-Id"])
    assert issuance.checksum == hashlib.sha256(pdf).hexdigest()
    assert issuance.size_bytes == len(pdf)

    # 3. Integrity verification of the downloaded copy.
    assert _verify(client, issuance.public_id, pdf).status_code == 204
    tampered = _verify(client, issuance.public_id, pdf.replace(b"Folio", b"Fol10"))
    assert tampered.status_code == 400

    # 4. The public code printed on the PDF confirms authenticity and folio.
    public = client.get(reverse("document-verify", args=[issuance.verification_code]))
    assert public.status_code == 200
    assert public.json()["valid"] is True
    assert public.json()["folio"] == issuance.folio

    actions = set(AuditEvent.objects.values_list("action", flat=True))
    assert {
        "documents.document.issued",
        "documents.individual_issuance.issued",
        "documents.individual_issuance.integrity_verified",
    } <= actions
