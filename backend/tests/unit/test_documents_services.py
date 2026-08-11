from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied

from apps.common.models import DomainError
from apps.documents.field_catalog import FIELD_TAG_CODES, FIELD_TAGS
from apps.documents.models import DocumentTemplate
from apps.documents.services import (
    create_document_template,
    deactivate_document_template,
    list_field_tags,
    update_document_template,
)
from tests.factories.academic import InstitutionFactory
from tests.factories.documents import DocumentTemplateFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# --------------------------------------------------------------------------- #
# create_document_template
# --------------------------------------------------------------------------- #


def test_create_document_template_normalises_code_to_upper_case():
    institution = InstitutionFactory()

    template = create_document_template(institution=institution, name="Constancia", code="  const ")

    assert template.code == "CONST"
    assert template.name == "Constancia"
    assert template.kind == DocumentTemplate.TemplateKind.OTHER
    assert template.is_active is True


def test_create_document_template_accepts_kind():
    template = create_document_template(
        institution=InstitutionFactory(),
        name="Certificado de estudios",
        code="CERT",
        kind=DocumentTemplate.TemplateKind.CERTIFICATE,
    )

    assert template.kind == DocumentTemplate.TemplateKind.CERTIFICATE


def test_create_document_template_rejects_duplicate_code_in_same_institution():
    institution = InstitutionFactory()
    create_document_template(institution=institution, name="Constancia", code="CONST")

    with pytest.raises(DomainError, match="already"):
        create_document_template(institution=institution, name="Otra", code="const")


def test_create_document_template_allows_same_code_in_different_institutions():
    first = create_document_template(institution=InstitutionFactory(), name="A", code="CONST")
    second = create_document_template(institution=InstitutionFactory(), name="A", code="CONST")

    assert first.pk != second.pk
    assert DocumentTemplate.objects.filter(code="CONST").count() == 2


def test_create_document_template_rejects_duplicate_code_even_when_existing_is_inactive():
    """Codes stay reserved: history is preserved, so reuse must be explicit."""
    institution = InstitutionFactory()
    existing = create_document_template(institution=institution, name="A", code="CONST")
    existing.is_active = False
    existing.save(update_fields=["is_active"])

    with pytest.raises(DomainError, match="already"):
        create_document_template(institution=institution, name="B", code="CONST")


def test_create_document_template_rejects_blank_code():
    with pytest.raises(DomainError, match="code"):
        create_document_template(institution=InstitutionFactory(), name="A", code="   ")


def test_create_document_template_rejects_blank_name():
    with pytest.raises(DomainError, match="name"):
        create_document_template(institution=InstitutionFactory(), name="  ", code="CONST")


# --------------------------------------------------------------------------- #
# update_document_template
# --------------------------------------------------------------------------- #


def test_update_document_template_changes_name_and_description():
    template = DocumentTemplateFactory(name="Old", description="")

    update_document_template(template=template, name="New", description="Updated")

    template.refresh_from_db()
    assert template.name == "New"
    assert template.description == "Updated"


def test_update_document_template_leaves_code_untouched():
    template = DocumentTemplateFactory(code="ORIGINAL")

    update_document_template(template=template, name="Renamed")

    template.refresh_from_db()
    assert template.code == "ORIGINAL"


# --------------------------------------------------------------------------- #
# deactivate_document_template
# --------------------------------------------------------------------------- #


def test_deactivate_document_template_preserves_the_record():
    template = DocumentTemplateFactory()

    deactivate_document_template(template=template)

    template.refresh_from_db()
    assert template.is_active is False
    assert DocumentTemplate.objects.filter(pk=template.pk).exists()


def test_deactivate_document_template_is_idempotent():
    template = DocumentTemplateFactory(is_active=False)

    deactivate_document_template(template=template)

    template.refresh_from_db()
    assert template.is_active is False


# --------------------------------------------------------------------------- #
# list_field_tags
# --------------------------------------------------------------------------- #


def test_list_field_tags_returns_the_fixed_catalogue_by_default():
    assert list_field_tags() == FIELD_TAGS


def test_field_tag_codes_are_unique():
    assert len(FIELD_TAG_CODES) == len(set(FIELD_TAG_CODES))


def test_current_field_catalogue_has_no_sensitive_tags():
    """
    RF-PLA-003: nothing medical or confidential is modelled yet, so today's
    catalogue must not mark anything sensitive. This guards against someone
    adding a sensitive tag without also reviewing the exclusion-by-default
    mechanism below.
    """
    assert all(sensitive is False for _code, _label, sensitive in FIELD_TAGS)


_FAKE_CATALOGUE = (
    ("student.full_name", "Nombre completo del estudiante", False),
    ("student.health_note", "Nota de salud (simulada para prueba)", True),
)


@patch("apps.documents.services.FIELD_TAGS", _FAKE_CATALOGUE)
def test_sensitive_tags_are_excluded_by_default():
    tags = list_field_tags()

    assert tags == (_FAKE_CATALOGUE[0],)


@patch("apps.documents.services.FIELD_TAGS", _FAKE_CATALOGUE)
def test_including_sensitive_tags_without_permission_is_denied():
    with pytest.raises(PermissionDenied):
        list_field_tags(actor=UserFactory(), include_sensitive=True)


@patch("apps.documents.services.FIELD_TAGS", _FAKE_CATALOGUE)
def test_including_sensitive_tags_without_actor_is_denied():
    with pytest.raises(PermissionDenied):
        list_field_tags(include_sensitive=True)


@patch("apps.documents.services.FIELD_TAGS", _FAKE_CATALOGUE)
def test_superuser_can_include_sensitive_tags():
    actor = UserFactory(is_superuser=True)

    tags = list_field_tags(actor=actor, include_sensitive=True)

    assert tags == _FAKE_CATALOGUE


@patch("apps.documents.services.FIELD_TAGS", _FAKE_CATALOGUE)
def test_actor_with_student_view_sensitive_can_include_sensitive_tags():
    permission = PermissionFactory(codename="student_view_sensitive")
    assignment = RoleAssignmentFactory(role=RoleFactory(permissions=[permission]))

    tags = list_field_tags(actor=assignment.user, include_sensitive=True)

    assert tags == _FAKE_CATALOGUE
