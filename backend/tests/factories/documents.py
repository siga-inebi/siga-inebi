import factory

from apps.documents.models import DocumentTemplate
from tests.factories.academic import InstitutionFactory


class DocumentTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentTemplate

    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"Template {n}")
    code = factory.Sequence(lambda n: f"TPL{n}")
    kind = DocumentTemplate.TemplateKind.OTHER
    description = ""
