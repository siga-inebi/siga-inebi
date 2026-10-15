"""RF-EMI-001: individual emission of constancias and certificados (services)."""

import hashlib
import re

import pytest

from apps.academics.services import close_academic_cycle
from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.documents.models import (
    DocumentIssuance,
    DocumentRecord,
    DocumentVerificationCode,
    OfficialFolio,
)
from apps.documents.services import (
    compile_generated_document,
    create_document_kind,
    create_document_template,
    issue_individual_document,
    verify_issued_document,
)
from apps.enrolments.services import create_enrolment, set_document_requirement
from tests.factories.academic import SectionFactory
from tests.factories.documents import DocumentTemplateFactory
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory
from tests.pdf_assertions import assert_pdf_structurally_valid

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

CONSTANCIA = DocumentIssuance.DocumentType.ENROLMENT_CERTIFICATE
CERTIFICADO = DocumentIssuance.DocumentType.STUDY_CERTIFICATE


def _enrolment():
    section = SectionFactory()
    return create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )


@pytest.fixture
def actor():
    return UserFactory(is_superuser=True)


def test_constancia_is_compiled_registered_and_never_stored(actor):
    """RF-EMI-001: emission registers folio, code, hash and audit without a stored file."""
    enrolment = _enrolment()

    issued = issue_individual_document(enrolment=enrolment, document_type=CONSTANCIA, actor=actor)

    issuance = issued.issuance
    assert issued.content_type == "application/pdf"
    assert b"CONSTANCIA DE INSCRIPCION" in issued.content
    assert enrolment.student.student_code.encode() in issued.content
    assert issuance.student_id == enrolment.student_id
    assert issuance.enrolment_id == enrolment.pk
    assert issuance.document_type == CONSTANCIA
    assert issuance.checksum == hashlib.sha256(issued.content).hexdigest()
    assert issuance.size_bytes == len(issued.content)
    assert issuance.issued_by_id == actor.pk
    assert re.fullmatch(r"[A-Z0-9]+-\d{4}-\d{4}", issuance.folio)
    assert issuance.folio.encode() in issued.content
    assert issuance.verification_code.encode() in issued.content
    assert DocumentVerificationCode.objects.filter(
        code=issuance.verification_code, folio=issuance.folio
    ).exists()
    assert AuditEvent.objects.filter(action="documents.document.issued").exists()
    assert AuditEvent.objects.filter(
        action="documents.individual_issuance.issued", resource_identifier=str(issuance.pk)
    ).exists()
    # RF-DOC-008: compiled on demand, nothing archived as a stored document.
    assert not DocumentRecord.objects.exists()
    assert_pdf_structurally_valid(issued.content)


def test_each_emission_takes_the_next_correlative_folio(actor):
    """RF-EMI-001 / RF-EMI-003: two emissions never share a folio."""
    enrolment = _enrolment()

    first = issue_individual_document(enrolment=enrolment, document_type=CONSTANCIA, actor=actor)
    second = issue_individual_document(enrolment=enrolment, document_type=CONSTANCIA, actor=actor)

    folios = OfficialFolio.objects.order_by("sequence")
    assert [folio.sequence for folio in folios] == [1, 2]
    assert first.issuance.folio != second.issuance.folio
    assert first.issuance.verification_code != second.issuance.verification_code


def test_constancia_uses_the_active_template_and_records_its_version(actor):
    """RF-EMI-001: the institutional template supplies the body and its version is kept."""
    enrolment = _enrolment()
    institution = enrolment.academic_cycle.institution
    create_document_kind(institution=institution, code="constancia", label="Constancia")
    template = create_document_template(
        institution=institution,
        name="Constancia de inscripcion",
        code="CONST",
        kind="constancia",
        content="Hacemos constar que {{student.full_name}} estudia en {{institution.name}}.",
    )

    issued = issue_individual_document(enrolment=enrolment, document_type=CONSTANCIA, actor=actor)

    person = enrolment.student.person
    assert f"Hacemos constar que {person.first_name}".encode() in issued.content
    assert issued.issuance.template_version == template.versions.get()


def test_certificado_requires_a_closed_cycle(actor):
    """RF-EMI-001: a certificado de estudios certifies a finished cycle only."""
    with pytest.raises(DomainError, match="ciclo cerrado"):
        issue_individual_document(enrolment=_enrolment(), document_type=CERTIFICADO, actor=actor)
    assert not DocumentIssuance.objects.exists()


def test_certificado_of_a_closed_cycle_prints_results_and_promotion(actor):
    """RF-EMI-001: certificate of a closed cycle reuses the boleta's frozen results."""
    enrolment = _enrolment()
    institution = enrolment.academic_cycle.institution
    DocumentTemplateFactory(institution=institution, kind="certificate", content="")
    close_academic_cycle(cycle=enrolment.academic_cycle)

    issued = issue_individual_document(enrolment=enrolment, document_type=CERTIFICADO, actor=actor)

    assert b"CERTIFICADO DE ESTUDIOS" in issued.content
    assert b"Condicion de promocion" in issued.content
    assert issued.issuance.document_type == CERTIFICADO
    assert_pdf_structurally_valid(issued.content)


def test_constancia_is_blocked_by_pending_required_documents(actor):
    """RF-EMI-001 / RF-EMI-004: pending required documents block the emission."""
    enrolment = _enrolment()
    set_document_requirement(enrolment=enrolment, code="BIRTH-CERT", name="Partida")

    with pytest.raises(DomainError, match="BIRTH-CERT"):
        issue_individual_document(enrolment=enrolment, document_type=CONSTANCIA, actor=actor)
    assert not DocumentIssuance.objects.exists()
    assert not OfficialFolio.objects.exists()


def test_unknown_individual_type_is_rejected(actor):
    """RF-EMI-001: only constancia and certificado are individual emissions."""
    with pytest.raises(DomainError, match="no admitido"):
        issue_individual_document(enrolment=_enrolment(), document_type="diploma", actor=actor)


def test_issuance_register_is_immutable(actor):
    """RF-EMI-001: the emission register cannot be rewritten or deleted."""
    issuance = issue_individual_document(
        enrolment=_enrolment(), document_type=CONSTANCIA, actor=actor
    ).issuance

    with pytest.raises(RuntimeError):
        issuance.save()
    with pytest.raises(RuntimeError):
        issuance.delete()
    with pytest.raises(RuntimeError):
        DocumentIssuance.objects.all().delete()
    with pytest.raises(RuntimeError):
        DocumentIssuance.objects.update(folio="X")


def test_issued_document_integrity_is_verified_by_sha256(actor):
    """RF-EMI-001: the delivered bytes verify; any alteration is detected."""
    issued = issue_individual_document(
        enrolment=_enrolment(), document_type=CONSTANCIA, actor=actor
    )

    assert verify_issued_document(actor=actor, issuance=issued.issuance, payload=issued.content)
    with pytest.raises(DomainError, match="no coincide"):
        verify_issued_document(
            actor=actor, issuance=issued.issuance, payload=issued.content + b"\n"
        )


def test_generic_generated_document_now_has_a_valid_xref():
    """RF-EMI-001: the shared assembler also fixes compile_generated_document (QA4-PDF-01)."""
    generated = compile_generated_document(
        template=DocumentTemplateFactory(),
        payload={"student_name": "Ana (Maria) Lopez", "folio": "DEMO-2026-0001"},
    )

    assert_pdf_structurally_valid(generated.content)
