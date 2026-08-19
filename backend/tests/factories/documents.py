import factory

from apps.documents.models import DocumentRecord, DocumentTemplate, DocumentTemplateVersion
from tests.factories.academic import InstitutionFactory
from tests.factories.students import StudentFactory


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


class DocumentRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentRecord

    student = factory.SubFactory(StudentFactory)
    filename = factory.Sequence(lambda n: f"record-{n}.pdf")
    storage_key = factory.Sequence(lambda n: f"local/record-{n}.pdf")
    content_type = "application/pdf"
    size_bytes = 256
    checksum = factory.Sequence(lambda n: f"sha256-{n}")
