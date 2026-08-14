import pytest
from django.db import IntegrityError

from apps.common.models import DomainError
from apps.documents.models import DocumentTemplate, DocumentTemplateVersion
from apps.documents.services import ensure_official_document_issuance_allowed
from apps.enrolments.models import EnrolmentDocumentRequirement
from apps.enrolments.services import create_enrolment, set_document_requirement
from tests.factories.academic import InstitutionFactory, SectionFactory
from tests.factories.documents import DocumentTemplateFactory, DocumentTemplateVersionFactory
from tests.factories.students import StudentFactory


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_document_template_code_is_unique_per_institution_at_db_level():
    institution = InstitutionFactory()
    DocumentTemplateFactory(institution=institution, code="CONST")

    with pytest.raises(IntegrityError):
        DocumentTemplate.objects.create(
            institution=institution,
            name="Otra",
            code="CONST",
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_document_template_code_can_repeat_across_institutions():
    first = DocumentTemplateFactory(institution=InstitutionFactory(), code="CONST")
    second = DocumentTemplateFactory(institution=InstitutionFactory(), code="CONST")

    assert first.pk != second.pk
    assert DocumentTemplate.objects.filter(code="CONST").count() == 2


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_document_template_version_sequence_is_unique_per_template_at_db_level():
    template = DocumentTemplateFactory()
    DocumentTemplateVersionFactory(template=template, sequence=1)

    with pytest.raises(IntegrityError):
        DocumentTemplateVersion.objects.create(
            template=template, sequence=1, name="Other", kind=DocumentTemplate.TemplateKind.OTHER
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_official_document_issuance_uses_enrolment_document_state():
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    set_document_requirement(
        enrolment=enrolment,
        code="GUARDIAN-ID",
        name="Guardian identity document",
    )

    with pytest.raises(DomainError, match="GUARDIAN-ID"):
        ensure_official_document_issuance_allowed(enrolment=enrolment)

    set_document_requirement(
        enrolment=enrolment,
        code="GUARDIAN-ID",
        name="Guardian identity document",
        status=EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED,
    )

    assert ensure_official_document_issuance_allowed(enrolment=enrolment) is True
