import pytest
from django.db import IntegrityError

from apps.documents.models import DocumentTemplate
from tests.factories.academic import InstitutionFactory
from tests.factories.documents import DocumentTemplateFactory


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
