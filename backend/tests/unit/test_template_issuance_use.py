"""D7 / #632: explicit use, atomic replacement and retained versions."""

import pytest
from django.db import IntegrityError, transaction

from apps.audit.models import AuditEvent
from apps.common.exceptions import DomainError
from apps.documents import queries, services
from apps.documents.models import DocumentTemplate
from tests.factories.academic import InstitutionFactory
from tests.factories.documents import DocumentTemplateFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_database_enforces_unique_active_use_even_when_service_is_bypassed():
    template = create(InstitutionFactory(), issuance_use="study_certificate")
    with pytest.raises(IntegrityError), transaction.atomic():
        DocumentTemplateFactory(institution=template.institution, issuance_use="study_certificate")


def test_availability_has_one_query_with_version_history(django_assert_num_queries):
    institution = InstitutionFactory()
    template = create(institution, issuance_use="study_certificate", content="Original")
    for index in range(5):
        services.update_document_template(template=template, content=f"Version {index}")
    with django_assert_num_queries(1):
        result = queries.template_issuance_uses(institution)
        assert len(result) == 2
        assert result[1]["uses_fallback"] is False


def create(institution, code="DEMO", **kwargs):
    return services.create_document_template(
        institution=institution, name=code, code=code, kind="certificate", **kwargs
    )


def test_kind_is_only_classification_and_omitted_use_means_none():
    institution = InstitutionFactory()
    first = create(institution)
    second = create(institution, "SECOND")
    assert first.issuance_use == second.issuance_use == "none"
    assert first.is_active and second.is_active


def test_same_use_conflicts_across_different_document_kinds():
    institution = InstitutionFactory()
    first = create(institution, issuance_use="enrolment_certificate")
    with pytest.raises(DomainError, match="uso"):
        services.create_document_template(
            institution=institution,
            name="Second",
            code="SECOND",
            kind="report",
            issuance_use="enrolment_certificate",
        )
    first.refresh_from_db()
    assert first.is_active
    assert DocumentTemplate.objects.filter(institution=institution).count() == 1


def test_explicit_replacement_is_audited_and_preserves_history():
    institution = InstitutionFactory()
    first = create(institution, issuance_use="study_certificate", content="Original")
    version = first.versions.get()
    second = create(
        institution,
        "NEXT",
        issuance_use="study_certificate",
        replaces_template_id=first.public_id,
        content="Replacement",
    )
    first.refresh_from_db()
    assert not first.is_active and second.is_active
    version.refresh_from_db()
    assert version.content == "Original"
    assert version.issuance_use == "study_certificate"
    assert second.versions.get().issuance_use == "study_certificate"
    assert AuditEvent.objects.filter(action="documents.template.replaced").exists()
    assert (
        services.get_active_document_template(
            institution=institution, issuance_use="study_certificate"
        )
        == second
    )


def test_stale_confirmation_does_not_replace_the_new_active_template():
    institution = InstitutionFactory()
    original = create(institution, issuance_use="study_certificate")
    current = create(
        institution,
        "CURRENT",
        issuance_use="study_certificate",
        replaces_template_id=original.public_id,
    )
    with pytest.raises(DomainError, match="cambi|confirm"):
        create(
            institution,
            "STALE",
            issuance_use="study_certificate",
            replaces_template_id=original.public_id,
        )
    current.refresh_from_db()
    assert current.is_active
    assert not DocumentTemplate.objects.filter(code="STALE").exists()


def test_replacement_rolls_back_when_new_template_code_conflicts():
    institution = InstitutionFactory()
    first = create(institution, issuance_use="study_certificate")
    with pytest.raises(DomainError):
        create(institution, issuance_use="study_certificate", replaces_template_id=first.public_id)
    first.refresh_from_db()
    assert first.is_active
    assert first.versions.count() == 1
    assert not AuditEvent.objects.filter(action="documents.template.replaced").exists()


def test_replacement_rolls_back_when_version_publication_fails(monkeypatch):
    institution = InstitutionFactory()
    first = create(institution, issuance_use="study_certificate")

    def fail(_template):
        raise DomainError("Version failed")

    monkeypatch.setattr(services, "_record_version", fail)
    with pytest.raises(DomainError, match="Version failed"):
        create(
            institution,
            "FAILED",
            issuance_use="study_certificate",
            replaces_template_id=first.public_id,
        )
    first.refresh_from_db()
    assert first.is_active
    assert not DocumentTemplate.objects.filter(code="FAILED").exists()


def test_update_preserves_use_on_omission_and_snapshots_changes():
    template = create(InstitutionFactory(), issuance_use="study_certificate")
    services.update_document_template(template=template, name="New name")
    template.refresh_from_db()
    assert template.issuance_use == "study_certificate"
    services.update_document_template(template=template, issuance_use="enrolment_certificate")
    assert list(template.versions.order_by("sequence").values_list("issuance_use", flat=True)) == [
        "study_certificate",
        "study_certificate",
        "enrolment_certificate",
    ]


def test_update_requires_confirmation_when_moving_to_an_occupied_use():
    institution = InstitutionFactory()
    first = create(institution, issuance_use="study_certificate")
    second = create(institution, "SECOND", issuance_use="enrolment_certificate")
    with pytest.raises(DomainError, match="uso"):
        services.update_document_template(template=second, issuance_use="study_certificate")
    services.update_document_template(
        template=second, issuance_use="study_certificate", replaces_template_id=first.public_id
    )
    first.refresh_from_db()
    second.refresh_from_db()
    assert not first.is_active and second.is_active
    assert second.issuance_use == "study_certificate"


@pytest.mark.parametrize("value", ["unknown", "", None])
def test_invalid_use_is_rejected_in_services(value):
    with pytest.raises(DomainError):
        create(InstitutionFactory(), issuance_use=value)


def test_cannot_replace_another_institution_or_replace_with_no_use():
    first = create(InstitutionFactory(), issuance_use="study_certificate")
    with pytest.raises(DomainError):
        create(
            InstitutionFactory(),
            issuance_use="study_certificate",
            replaces_template_id=first.public_id,
        )
    with pytest.raises(DomainError):
        create(first.institution, "NONE", replaces_template_id=first.public_id)
    first.refresh_from_db()
    assert first.is_active


def test_availability_comes_from_use_and_latest_published_version():
    institution = InstitutionFactory()
    unrelated = DocumentTemplateFactory(issuance_use="study_certificate")
    template = create(institution, issuance_use="study_certificate", content="Hello")
    uses = {row["code"]: row for row in queries.template_issuance_uses(institution)}
    assert uses["enrolment_certificate"]["uses_fallback"] is True
    assert uses["enrolment_certificate"]["active_template"] is None
    assert uses["study_certificate"]["active_template"]["public_id"] == template.public_id
    assert uses["study_certificate"]["uses_fallback"] is False
    assert uses["study_certificate"]["active_template"]["public_id"] != unrelated.public_id
    services.update_document_template(template=template, content="")
    assert (
        next(
            row
            for row in queries.template_issuance_uses(institution)
            if row["code"] == "study_certificate"
        )["uses_fallback"]
        is True
    )


def test_issuance_resolves_use_without_any_document_kind_code_convention():
    institution = InstitutionFactory()
    template = services.create_document_template(
        institution=institution,
        name="Custom",
        code="CUSTOM",
        kind="report",
        issuance_use="study_certificate",
        content="Custom body",
    )
    version = services._active_template_version(
        institution=institution, issuance_use="study_certificate"
    )
    assert version.template_id == template.pk
    assert version.content == "Custom body"
    assert (
        services._active_template_version(
            institution=institution, issuance_use="enrolment_certificate"
        )
        is None
    )
