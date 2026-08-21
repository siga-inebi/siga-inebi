from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditEvent
from apps.common.exceptions import AuthorizationError
from apps.common.models import DomainError
from apps.documents.field_catalog import FIELD_TAG_CODES, FIELD_TAGS
from apps.documents.models import DocumentRecord, DocumentTemplate
from apps.documents.services import (
    compile_generated_document,
    create_document_template,
    deactivate_document_record,
    deactivate_document_template,
    ensure_document_access,
    ensure_official_document_issuance_allowed,
    ensure_official_document_issuance_permission,
    evaluate_official_document_issuance,
    get_active_document_template,
    issue_document_download_token,
    issue_official_document_folio,
    list_document_types,
    list_field_tags,
    normalize_document_filename,
    record_document_read_audit,
    student_document_dossier,
    update_document_template,
    validate_document_download_token,
    validate_document_upload,
)
from apps.enrolments.models import EnrolmentDocumentRequirement
from apps.enrolments.services import create_enrolment, set_document_requirement
from tests.factories.academic import InstitutionFactory, SectionFactory
from tests.factories.documents import DocumentTemplateFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.students import StudentFactory

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


def test_validate_document_upload_accepts_supported_pdf_and_image_types():
    allowed = [
        SimpleUploadedFile("constancia.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
        SimpleUploadedFile("dni.JPG", b"fake-jpg-bytes", content_type="image/jpeg"),
        SimpleUploadedFile("foto.png", b"fake-png-bytes", content_type="image/png"),
    ]

    for upload in allowed:
        validated = validate_document_upload(upload)
        assert validated["content_type"] in {"application/pdf", "image/jpeg", "image/png"}
        assert validated["size_bytes"] == len(upload.read())
        upload.seek(0)


def test_validate_document_upload_rejects_unsupported_extension_and_oversized_payload():
    with pytest.raises(DomainError, match="not supported|unsupported"):
        validate_document_upload(
            SimpleUploadedFile(
                "document.exe",
                b"bad",
                content_type="application/x-msdownload",
            )
        )

    oversized = SimpleUploadedFile(
        "big.pdf",
        b"%PDF-1.4 " + b"A" * (10 * 1024 * 1024),
        content_type="application/pdf",
    )
    with pytest.raises(DomainError, match="size|too large|maximum"):
        validate_document_upload(oversized)


def test_normalize_document_filename_keeps_safe_and_stable_basename():
    assert (
        normalize_document_filename("  Mi Documento (oficial).PDF  ") == "mi-documento-oficial.pdf"
    )
    assert normalize_document_filename("../weird name.png") == "weird-name.png"


def _enrolment():
    section = SectionFactory()
    return create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )


def test_official_document_issuance_is_allowed_without_pending_required_documents():
    assert ensure_official_document_issuance_allowed(enrolment=_enrolment()) is True


def test_official_document_issuance_is_blocked_by_pending_required_documents():
    enrolment = _enrolment()
    set_document_requirement(
        enrolment=enrolment,
        code="BIRTH-CERT",
        name="Birth certificate",
        status=EnrolmentDocumentRequirement.DeliveryStatus.PENDING,
    )

    with pytest.raises(DomainError, match="BIRTH-CERT"):
        ensure_official_document_issuance_allowed(enrolment=enrolment)


def test_official_document_issuance_ignores_pending_optional_documents():
    enrolment = _enrolment()
    set_document_requirement(
        enrolment=enrolment,
        code="PHOTO",
        name="Student photo",
        status=EnrolmentDocumentRequirement.DeliveryStatus.PENDING,
        is_required=False,
    )

    assert ensure_official_document_issuance_allowed(enrolment=enrolment) is True


def test_official_document_issuance_ignores_pending_inactive_documents():
    enrolment = _enrolment()
    requirement = set_document_requirement(
        enrolment=enrolment,
        code="OLD-FORM",
        name="Superseded form",
        status=EnrolmentDocumentRequirement.DeliveryStatus.PENDING,
    )
    # ``set_document_requirement`` always reactivates the requirement it writes and
    # no service deactivates one yet, so the state is set directly here.
    requirement.is_active = False
    requirement.save(update_fields=["is_active", "updated_at"])

    assert ensure_official_document_issuance_allowed(enrolment=enrolment) is True


def test_official_document_issuance_returns_every_blocking_code():
    enrolment = _enrolment()
    set_document_requirement(enrolment=enrolment, code="BIRTH-CERT", name="Birth certificate")
    set_document_requirement(enrolment=enrolment, code="GUARDIAN-ID", name="Guardian ID")

    blocking_codes = evaluate_official_document_issuance(enrolment=enrolment)

    assert blocking_codes == ["BIRTH-CERT", "GUARDIAN-ID"]


def test_official_document_issuance_permission_is_denied_without_actor():
    with pytest.raises(AuthorizationError):
        ensure_official_document_issuance_permission(actor=None)


def test_official_document_issuance_permission_is_denied_without_the_permission():
    with pytest.raises(AuthorizationError):
        ensure_official_document_issuance_permission(actor=UserFactory())


def test_superuser_passes_the_official_document_issuance_permission():
    actor = UserFactory(is_superuser=True)

    assert ensure_official_document_issuance_permission(actor=actor) is True


def test_actor_with_document_issue_passes_the_official_document_issuance_permission():
    permission = PermissionFactory(codename="document_issue")
    assignment = RoleAssignmentFactory(role=RoleFactory(permissions=[permission]))

    assert ensure_official_document_issuance_permission(actor=assignment.user) is True


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


def test_deactivate_document_template_does_not_record_a_version():
    template = create_document_template(institution=InstitutionFactory(), name="A", code="A")

    deactivate_document_template(template=template)

    assert template.versions.count() == 1


def test_document_template_delete_is_blocked_to_preserve_history():
    template = DocumentTemplateFactory()

    with pytest.raises(RuntimeError, match="cannot be deleted"):
        template.delete()


def test_enrolment_document_requirement_delete_is_blocked_to_preserve_history():
    enrolment = _enrolment()
    requirement = set_document_requirement(
        enrolment=enrolment,
        code="BIRTH-CERT",
        name="Birth certificate",
    )

    with pytest.raises(RuntimeError, match="cannot be deleted"):
        requirement.delete()


def test_document_record_is_soft_deactivated_instead_of_deleted():
    student = StudentFactory()
    record = DocumentRecord.objects.create(
        student=student,
        filename="birth-certificate.pdf",
        storage_key="local/birth-certificate.pdf",
        content_type="application/pdf",
        size_bytes=256,
        checksum="abc123",
    )

    deactivate_document_record(record=record)

    record.refresh_from_db()
    assert record.is_active is False
    assert DocumentRecord.objects.filter(pk=record.pk).exists()


def test_document_record_delete_is_blocked_to_preserve_history():
    student = StudentFactory()
    record = DocumentRecord.objects.create(
        student=student,
        filename="guardian-id.png",
        storage_key="local/guardian-id.png",
        content_type="image/png",
        size_bytes=128,
        checksum="def456",
    )

    with pytest.raises(RuntimeError, match="cannot be deleted"):
        record.delete()


def test_document_record_links_cannot_be_reassigned_after_creation():
    student = StudentFactory()
    enrolment = _enrolment()
    record = DocumentRecord.objects.create(
        student=student,
        enrolment=enrolment,
        filename="student-link.pdf",
        storage_key="local/student-link.pdf",
        content_type="application/pdf",
        size_bytes=512,
        checksum="ghi789",
    )

    new_student = StudentFactory()
    with pytest.raises(RuntimeError, match="cannot be modified|link"):
        record.student = new_student
        record.save(update_fields=["student"])

    new_enrolment = _enrolment()
    with pytest.raises(RuntimeError, match="cannot be modified|link"):
        record.enrolment = new_enrolment
        record.save(update_fields=["enrolment"])


# --------------------------------------------------------------------------- #
# versioning (RF-PLA-005)
# --------------------------------------------------------------------------- #


def test_create_document_template_records_initial_version():
    template = create_document_template(
        institution=InstitutionFactory(), name="Constancia", code="CONST", description="v1"
    )

    versions = list(template.versions.all())
    assert len(versions) == 1
    assert versions[0].sequence == 1
    assert versions[0].name == "Constancia"
    assert versions[0].description == "v1"


def test_update_document_template_records_a_new_version():
    template = create_document_template(institution=InstitutionFactory(), name="Old", code="A")

    update_document_template(template=template, name="New")

    versions = list(template.versions.order_by("sequence"))
    assert [v.sequence for v in versions] == [1, 2]
    assert versions[0].name == "Old"
    assert versions[1].name == "New"


def test_update_document_template_with_nothing_to_change_does_not_record_a_version():
    template = create_document_template(institution=InstitutionFactory(), name="A", code="A")

    update_document_template(template=template)

    assert template.versions.count() == 1


def test_document_template_version_cannot_be_modified():
    version = create_document_template(
        institution=InstitutionFactory(), name="A", code="A"
    ).versions.get()

    version.name = "Tampered"
    with pytest.raises(RuntimeError):
        version.save()


def test_document_template_version_cannot_be_deleted():
    version = create_document_template(
        institution=InstitutionFactory(), name="A", code="A"
    ).versions.get()

    with pytest.raises(RuntimeError):
        version.delete()


# --------------------------------------------------------------------------- #
# institutional_header (RF-PLA-004)
# --------------------------------------------------------------------------- #


def test_institutional_header_reflects_current_institution_data():
    institution = InstitutionFactory(name="Instituto Demo", short_name="DEMO")
    template = DocumentTemplateFactory(institution=institution)

    assert template.institutional_header == {
        "institution_name": "Instituto Demo",
        "institution_short_name": "DEMO",
        "logo_url": None,
    }


def test_institutional_header_follows_institution_changes():
    """Derived, not stored: renaming the institution changes the header immediately."""
    institution = InstitutionFactory(name="Old Name")
    template = DocumentTemplateFactory(institution=institution)

    institution.name = "New Name"
    institution.save(update_fields=["name"])

    assert template.institutional_header["institution_name"] == "New Name"


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
    with pytest.raises(AuthorizationError):
        list_field_tags(actor=UserFactory(), include_sensitive=True)


@patch("apps.documents.services.FIELD_TAGS", _FAKE_CATALOGUE)
def test_including_sensitive_tags_without_actor_is_denied():
    with pytest.raises(AuthorizationError):
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


def test_document_read_audit_is_recorded_for_authorized_users():
    permission = PermissionFactory(codename="document_read")
    assignment = RoleAssignmentFactory(role=RoleFactory(permissions=[permission]))

    record_document_read_audit(actor=assignment.user, subject=StudentFactory())

    assert AuditEvent.objects.filter(action="documents.document.read").exists()


def test_document_read_audit_logs_denial_for_unauthorized_users():
    with pytest.raises(AuthorizationError, match="read documents"):
        record_document_read_audit(actor=UserFactory(), subject=StudentFactory())

    assert AuditEvent.objects.filter(action="documents.document.read_denied").exists()


def test_list_document_types_returns_the_fixed_catalogue():
    assert list_document_types() == (
        ("certificate", "Certificado"),
        ("report", "Reporte"),
        ("other", "Otro"),
    )


def test_get_active_document_template_requires_a_single_active_template_per_kind():
    institution = InstitutionFactory()
    certificate = create_document_template(
        institution=institution,
        name="Certificado",
        code="CERT",
        kind=DocumentTemplate.TemplateKind.CERTIFICATE,
    )
    create_document_template(
        institution=institution,
        name="Certificado viejo",
        code="CERT-OLD",
        kind=DocumentTemplate.TemplateKind.CERTIFICATE,
        is_active=False,
    )

    assert get_active_document_template(institution=institution, kind="certificate") == certificate

    with pytest.raises(
        DomainError,
        match="active.*document template|already exists.*document type|document type.*active",
    ):
        create_document_template(
            institution=institution,
            name="Segundo certificado",
            code="CERT-2",
            kind=DocumentTemplate.TemplateKind.CERTIFICATE,
        )

    certificate.is_active = False
    certificate.save(update_fields=["is_active", "updated_at"])
    second = create_document_template(
        institution=institution,
        name="Segundo certificado",
        code="CERT-2",
        kind=DocumentTemplate.TemplateKind.CERTIFICATE,
    )

    assert get_active_document_template(institution=institution, kind="certificate") == second

    second.is_active = False
    second.save(update_fields=["is_active", "updated_at"])


def test_document_access_requires_permission_and_scope():
    student = StudentFactory()
    actor = UserFactory()
    permission = PermissionFactory(codename="document_read")
    assignment = RoleAssignmentFactory(user=actor, role=RoleFactory(permissions=[permission]))

    with pytest.raises(AuthorizationError, match="scope|read documents"):
        ensure_document_access(actor=actor, student=student)

    ScopeGrantFactory(assignment=assignment, student=student)

    assert ensure_document_access(actor=actor, student=student) is True


def test_document_download_tokens_are_issued_and_validated():
    actor = UserFactory()
    permission = PermissionFactory(codename="document_read")
    assignment = RoleAssignmentFactory(user=actor, role=RoleFactory(permissions=[permission]))
    student = StudentFactory()
    ScopeGrantFactory(assignment=assignment, student=student)
    document = DocumentRecord.objects.create(
        student=student,
        filename="birth-certificate.pdf",
        storage_key="local/birth-certificate.pdf",
        content_type="application/pdf",
        size_bytes=256,
        checksum="abc123",
    )

    token = issue_document_download_token(actor=actor, document=document)

    assert token.token
    assert validate_document_download_token(document=document, token=token.token) is True
    with pytest.raises(DomainError, match="valid|token"):
        validate_document_download_token(document=document, token="invalid-token")


def test_generated_documents_are_compiled_in_memory_and_never_persisted():
    template = DocumentTemplateFactory()

    generated = compile_generated_document(
        template=template,
        payload={"student_name": "Ana López", "document_type": "Constancia"},
    )

    assert generated.persisted is False
    assert generated.storage_key is None
    assert generated.content_type == "application/pdf"
    assert generated.content.startswith(b"%PDF")
    assert DocumentRecord.objects.filter(storage_key=generated.storage_key).count() == 0


def test_generated_documents_refuse_persistence_to_storage():
    template = DocumentTemplateFactory()

    with pytest.raises(DomainError, match="persist|storage"):
        compile_generated_document(
            template=template, payload={"student_name": "Ana López"}, persist=True
        )


def test_generated_documents_include_the_issuance_timestamp_and_folio_when_available():
    template = DocumentTemplateFactory(kind=DocumentTemplate.TemplateKind.CERTIFICATE)
    issued_at = "2026-08-18T12:30:45-03:00"
    folio = "DOC-2026-0001"

    generated = compile_generated_document(
        template=template,
        payload={
            "student_name": "Ana López",
            "document_type": "Certificado",
            "issued_at": issued_at,
            "folio": folio,
        },
    )

    assert generated.issued_at == issued_at
    assert generated.folio == folio
    assert folio.encode() in generated.content
    assert b"2026-08-18" in generated.content


def test_issue_official_document_folio_increments_by_institution():
    institution = InstitutionFactory(short_name="INEBI")

    first = issue_official_document_folio(
        institution=institution,
        issued_at=datetime(2026, 8, 18, 12, 30, 45, tzinfo=UTC),
    )
    second = issue_official_document_folio(
        institution=institution,
        issued_at=datetime(2026, 8, 18, 13, 0, tzinfo=UTC),
    )

    assert first.startswith("INEBI-2026-")
    assert second.startswith("INEBI-2026-")
    assert first.endswith("0001")
    assert second.endswith("0002")


def test_student_document_dossier_includes_document_records_for_the_student():
    student = StudentFactory()
    first_section = SectionFactory()
    first_enrolment = create_enrolment(
        student=student,
        academic_cycle=first_section.academic_cycle,
        grade=first_section.grade,
        section=first_section,
    )
    DocumentRecord.objects.create(
        student=student,
        enrolment=first_enrolment,
        filename="birth-certificate.pdf",
        storage_key="local/birth-certificate.pdf",
        content_type="application/pdf",
        size_bytes=256,
        checksum="abc123",
    )
    set_document_requirement(
        enrolment=first_enrolment,
        code="BIRTH-CERT",
        name="Birth certificate",
        status=EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED,
    )

    dossier = student_document_dossier(student=student)

    assert dossier["documents"][0]["filename"] == "birth-certificate.pdf"
    assert dossier["documents"][0]["storage_key"] == "local/birth-certificate.pdf"
    assert dossier["documents"][0]["status"] == DocumentRecord.StorageStatus.ACTIVE


def test_student_document_dossier_lists_all_enrolments_and_requirements():
    student = StudentFactory()
    first_section = SectionFactory()
    second_section = SectionFactory()
    first_enrolment = create_enrolment(
        student=student,
        academic_cycle=first_section.academic_cycle,
        grade=first_section.grade,
        section=first_section,
    )
    # Cerrada antes de abrir la siguiente: un estudiante tiene una sola matricula
    # activa, y el expediente es justamente lo que junta la cerrada con la nueva.
    first_enrolment.status = first_enrolment.EnrolmentStatus.COMPLETED
    first_enrolment.save(update_fields=["status", "updated_at"])
    second_enrolment = create_enrolment(
        student=student,
        academic_cycle=second_section.academic_cycle,
        grade=second_section.grade,
        section=second_section,
    )
    set_document_requirement(
        enrolment=first_enrolment,
        code="BIRTH-CERT",
        name="Birth certificate",
        status=EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED,
    )
    set_document_requirement(
        enrolment=second_enrolment,
        code="GUARDIAN-ID",
        name="Guardian ID",
    )

    dossier = student_document_dossier(student=student)

    assert len(dossier["enrolments"]) == 2
    assert {entry["enrolment_id"] for entry in dossier["enrolments"]} == {
        str(first_enrolment.public_id),
        str(second_enrolment.public_id),
    }
    assert {item["code"] for item in dossier["requirements"]} == {"BIRTH-CERT", "GUARDIAN-ID"}
