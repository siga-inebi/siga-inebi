"""RF-EMI-001: REST contract of the individual emission of constancias and certificados."""

import hashlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.academics.services import close_academic_cycle
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

pytestmark = [pytest.mark.api, pytest.mark.django_db]

MISSING_UUID = "00000000-0000-0000-0000-000000000000"


def _enrolment():
    section = SectionFactory()
    return create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )


def _login(client, *codenames, **scope):
    user = UserFactory()
    permissions = [PermissionFactory(codename=codename) for codename in codenames]
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=permissions))
    if scope:
        ScopeGrantFactory(assignment=assignment, **scope)
    client.force_login(user)
    return user


def _upload(payload):
    return SimpleUploadedFile("emitido.pdf", payload, content_type="application/pdf")


def _issue(client, enrolment_id, document_type="enrolment_certificate"):
    return client.post(
        reverse("document-individual-issuance"),
        {"enrolment_id": str(enrolment_id), "document_type": document_type},
        content_type="application/json",
    )


@pytest.mark.security
@pytest.mark.parametrize(
    ("url_name", "kwargs"),
    [
        ("document-individual-issuance", {}),
        ("document-issuance-integrity-verify", {"public_id": MISSING_UUID}),
    ],
)
def test_individual_issuance_endpoints_require_authentication(client, url_name, kwargs):
    """RF-EMI-001: anonymous callers cannot emit or verify."""
    response = client.post(reverse(url_name, kwargs=kwargs))

    assert response.status_code in (401, 403)


def test_constancia_is_returned_as_pdf_with_issuance_headers(client):
    """RF-EMI-001: 201 with the PDF and the registered folio, hash and code."""
    enrolment = _enrolment()
    _login(client, "document_issue", student=enrolment.student)

    response = _issue(client, enrolment.public_id)

    assert response.status_code == 201
    assert response["Content-Type"] == "application/pdf"
    assert "attachment" in response["Content-Disposition"]
    issuance = DocumentIssuance.objects.get()
    assert response["X-Document-Issuance-Id"] == str(issuance.public_id)
    assert response["X-Document-Folio"] == issuance.folio
    assert response["X-Document-Verification-Code"] == issuance.verification_code
    assert response["X-Document-Checksum"] == hashlib.sha256(response.content).hexdigest()
    assert_pdf_structurally_valid(response.content)


def test_certificado_of_a_closed_cycle_is_issued(client):
    """RF-EMI-001: the certificado de estudios is issued for a closed cycle."""
    enrolment = _enrolment()
    close_academic_cycle(cycle=enrolment.academic_cycle)
    _login(client, "document_issue", student=enrolment.student)

    response = _issue(client, enrolment.public_id, "study_certificate")

    assert response.status_code == 201
    assert b"CERTIFICADO DE ESTUDIOS" in response.content
    assert_pdf_structurally_valid(response.content)


def test_certificado_of_an_open_cycle_is_rejected(client):
    """RF-EMI-001: open cycle -> 400, nothing registered."""
    enrolment = _enrolment()
    _login(client, "document_issue", student=enrolment.student)

    response = _issue(client, enrolment.public_id, "study_certificate")

    assert response.status_code == 400
    assert not DocumentIssuance.objects.exists()


def test_unknown_document_type_is_rejected(client):
    """RF-EMI-001: only the two individual types are accepted."""
    enrolment = _enrolment()
    _login(client, "document_issue", student=enrolment.student)

    assert _issue(client, enrolment.public_id, "diploma").status_code == 400


def test_unknown_enrolment_returns_404_for_an_authorized_caller(client):
    """RF-EMI-001: missing enrolment -> 404 once the permission is held."""
    _login(client, "document_issue", module_key="students")

    assert _issue(client, MISSING_UUID).status_code == 404


@pytest.mark.security
def test_emission_without_permission_is_forbidden_even_for_unknown_enrolments(client):
    """RF-EMI-001: no permission -> 403 before resolving the enrolment (no probing)."""
    enrolment = _enrolment()
    _login(client, "document_read", student=enrolment.student)

    assert _issue(client, enrolment.public_id).status_code == 403
    assert _issue(client, MISSING_UUID).status_code == 403


@pytest.mark.security
def test_emission_out_of_scope_is_forbidden(client):
    """RF-EMI-001: permission over another student -> 403, nothing registered."""
    enrolment = _enrolment()
    _login(client, "document_issue", student=StudentFactory())

    response = _issue(client, enrolment.public_id)

    assert response.status_code == 403
    assert not DocumentIssuance.objects.exists()


@pytest.mark.security
def test_verifying_out_of_scope_is_forbidden(client):
    """RF-EMI-001: integrity verification needs read scope over the student."""
    enrolment = _enrolment()
    _login(client, "document_issue", student=enrolment.student)
    issued = _issue(client, enrolment.public_id)
    _login(client, "document_read", student=StudentFactory())

    response = client.post(
        reverse("document-issuance-integrity-verify", args=[issued["X-Document-Issuance-Id"]]),
        {"file": _upload(issued.content)},
    )

    assert response.status_code == 403


def test_verifying_an_unknown_issuance_returns_404(client):
    """RF-EMI-001: unknown issuance id -> 404."""
    _login(client, "document_read", module_key="students")

    response = client.post(
        reverse("document-issuance-integrity-verify", args=[MISSING_UUID]),
        {"file": _upload(b"%PDF-1.4")},
    )

    assert response.status_code == 404
