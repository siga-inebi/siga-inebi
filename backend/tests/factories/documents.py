import factory

from apps.documents.models import DocumentTemplate, DocumentTemplateVersion
from tests.factories.academic import InstitutionFactory


class DocumentTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentTemplate

    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"Template {n}")
    code = factory.Sequence(lambda n: f"TPL{n}")
    kind = DocumentTemplate.TemplateKind.OTHER
    description = ""


class DocumentTemplateVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentTemplateVersion

    template = factory.SubFactory(DocumentTemplateFactory)
    sequence = factory.Sequence(lambda n: n + 1)
    name = factory.Sequence(lambda n: f"Template {n}")
    kind = DocumentTemplate.TemplateKind.OTHER
    description = ""
