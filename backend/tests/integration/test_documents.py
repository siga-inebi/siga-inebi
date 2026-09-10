from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.academics.models import CurriculumPlan
from apps.academics.queries import latest_frozen_subject_result
from apps.academics.services import close_academic_cycle
from apps.common.models import DomainError
from apps.documents.models import DocumentTemplate, DocumentTemplateVersion
from apps.documents.services import (
    compile_historical_cycle_report,
    ensure_official_document_issuance_allowed,
)
from apps.enrolments.models import EnrolmentDocumentRequirement
from apps.enrolments.services import create_enrolment, set_document_requirement
from apps.evaluation.services import (
    close_evaluation_unit,
    create_evaluation_unit,
    register_unit_grade,
)
from tests.factories.academic import (
    AcademicCycleFactory,
    InstitutionFactory,
    SectionFactory,
    SubjectFactory,
)
from tests.factories.documents import DocumentTemplateFactory, DocumentTemplateVersionFactory
from tests.factories.people import PersonFactory
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


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_boleta_crosses_academics_evaluation_and_enrolments_via_the_frozen_result():
    """
    RF-RES-008: compile_historical_cycle_report (documents) reads the
    RF-RES-007 freeze (academics) that was itself derived from evaluation
    grades and enrolments.determine_promotion -- one flow across four
    domains, matching what the system used to decide each condition.
    """
    cycle = AcademicCycleFactory(status="active")
    today = timezone.localdate()
    unit = create_evaluation_unit(
        academic_cycle=cycle,
        number=1,
        name="Unidad 1",
        starts_on=cycle.starts_on,
        ends_on=cycle.starts_on + timedelta(days=30),
        capture_starts_on=today - timedelta(days=5),
        capture_ends_on=today + timedelta(days=5),
    )
    section = SectionFactory(academic_cycle=cycle)
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=cycle,
        grade=section.grade,
        section=section,
    )
    subject = SubjectFactory(institution=cycle.institution, name="Lenguaje")
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=section.grade, subject=subject)
    register_unit_grade(
        enrolment=enrolment,
        subject=subject,
        evaluation_unit=unit,
        teacher=PersonFactory(),
        value=72,
    )
    close_evaluation_unit(unit)
    close_academic_cycle(cycle=cycle)

    frozen = latest_frozen_subject_result(enrolment=enrolment, subject=subject)
    report = compile_historical_cycle_report(enrolment=enrolment)

    assert frozen is not None
    assert frozen.final_grade == 72
    assert f"Nota final: {frozen.final_grade}".encode() in report.content
    assert b"Aprobado" in report.content
    assert b"Promovido" in report.content
