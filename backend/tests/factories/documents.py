import factory

from apps.documents.models import (
    DocumentKind,
    DocumentRecord,
    DocumentTemplate,
    DocumentTemplateVersion,
)
from tests.factories.academic import InstitutionFactory
from tests.factories.students import StudentFactory


class DocumentKindFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentKind

    institution = factory.SubFactory(InstitutionFactory)
    code = factory.Sequence(lambda n: f"kind-{n}")
    label = factory.Sequence(lambda n: f"Tipo {n}")
    description = ""


class DocumentTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentTemplate

    class Params:
        # Callers still say ``kind="certificate"``: the parameter now resolves a
        # row of the institution's catalogue instead of an enum member
        # (RNF-MAN-001). The type is looked up in the template's OWN
        # institution -- a SubFactory would build a second institution and
        # point the template at a type its institution does not offer.
        kind = "other"

    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"Template {n}")
    code = factory.Sequence(lambda n: f"TPL{n}")
    document_kind = factory.LazyAttribute(
        lambda obj: DocumentKind.objects.get_or_create(
            institution=obj.institution,
            code=obj.kind,
            defaults={"label": obj.kind.replace("-", " ").title()},
        )[0]
    )
    description = ""


class DocumentTemplateVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentTemplateVersion

    template = factory.SubFactory(DocumentTemplateFactory)
    sequence = factory.Sequence(lambda n: n + 1)
    name = factory.Sequence(lambda n: f"Template {n}")
    kind = "other"
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
