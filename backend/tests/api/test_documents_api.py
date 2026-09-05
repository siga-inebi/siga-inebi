import pytest
from django.urls import reverse

from apps.academics.services import close_academic_cycle
from apps.audit.models import AuditEvent
from apps.documents.field_catalog import FIELD_TAG_CODES
from apps.documents.models import DocumentTemplate
from apps.documents.services import compile_generated_document
from apps.enrolments.services import create_enrolment, set_document_requirement
from tests.factories.academic import SectionFactory
from tests.factories.documents import DocumentTemplateFactory, DocumentTemplateVersionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.students import GuardianFactory, StudentFactory, StudentGuardianRelationFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

MISSING_UUID = "00000000-0000-0000-0000-000000000000"


def _detail(response):
    return response.json()["error"]["detail"]


def _items(response):
    return response.json()["results"]


# --------------------------------------------------------------------------- #
# authentication
# --------------------------------------------------------------------------- #


@pytest.mark.security
@pytest.mark.parametrize("url_name", ["document-template-list-create", "document-field-tag-list"])
def test_document_endpoints_require_authentication(client, url_name):
    response = client.get(reverse(url_name))

    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------- #
# create / list
# --------------------------------------------------------------------------- #


def test_create_document_template_returns_201_with_public_id(auth_client, institution):
    response = auth_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia de estudios", "code": "const", "kind": "certificate"},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "CONST"
    assert body["kind"] == "certificate"
    assert "public_id" in body
    assert DocumentTemplate.objects.filter(institution=institution, code="CONST").exists()


def test_document_template_response_includes_institutional_header(auth_client, institution):
    template = DocumentTemplateFactory(institution=institution)

    response = auth_client.get(reverse("document-template-detail", args=[template.public_id]))

    assert response.status_code == 200
    header = response.json()["header"]
    assert header["institution_name"] == institution.name
    assert header["institution_short_name"] == institution.short_name
    assert header["logo_url"] is None


def test_document_delivery_receipt_can_be_created(auth_client):
    student = StudentFactory()
    guardian = GuardianFactory()
    StudentGuardianRelationFactory(student=student, guardian=guardian, is_primary=True)

    response = auth_client.post(
        reverse("document-delivery-receipt-create"),
        {
            "student_id": str(student.public_id),
            "guardian_id": str(guardian.public_id),
            "document_type": "Certificado",
            "recipient_name": "Ana López",
            "folio": "DOC-2026-0001",
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["document_type"] == "Certificado"
    assert body["student_id"] == str(student.public_id)
    assert body["guardian_id"] == str(guardian.public_id)


def test_document_template_header_ignores_submitted_value_on_create(auth_client, institution):
    response = auth_client.post(
        reverse("document-template-list-create"),
        {
            "name": "Constancia",
            "code": "CONST",
            "header": {"institution_name": "Suplantado", "logo_url": "http://evil.example/x.png"},
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["header"]["institution_name"] == institution.name


def test_document_template_header_ignores_submitted_value_on_update(auth_client, institution):
    template = DocumentTemplateFactory(institution=institution)

    response = auth_client.patch(
        reverse("document-template-detail", args=[template.public_id]),
        {"header": {"institution_name": "Suplantado"}},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["header"]["institution_name"] == institution.name


def test_create_document_template_rejects_duplicate_code_with_400(auth_client, institution):
    DocumentTemplateFactory(institution=institution, code="CONST")

    response = auth_client.post(
        reverse("document-template-list-create"),
        {"name": "Otra", "code": "CONST"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "already" in str(_detail(response))


def test_create_document_template_rejects_missing_code_with_field_error(auth_client, institution):
    response = auth_client.post(
        reverse("document-template-list-create"),
        {"name": "Sin codigo"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "code" in _detail(response)


def test_list_document_templates_only_returns_current_institution(auth_client, institution):
    DocumentTemplateFactory(institution=institution, code="CONST")
    DocumentTemplateFactory(code="OTHER")  # another institution

    response = auth_client.get(reverse("document-template-list-create"))

    assert response.status_code == 200
    codes = [item["code"] for item in _items(response)]
    assert codes == ["CONST"]


def test_list_document_templates_hides_inactive_by_default_and_shows_them_on_request(
    auth_client, institution
):
    DocumentTemplateFactory(institution=institution, code="ACTIVE")
    DocumentTemplateFactory(institution=institution, code="INACTIVE", is_active=False)

    default = auth_client.get(reverse("document-template-list-create"))
    included = auth_client.get(
        reverse("document-template-list-create"), {"include_inactive": "true"}
    )

    assert [item["code"] for item in _items(default)] == ["ACTIVE"]
    assert sorted(item["code"] for item in _items(included)) == ["ACTIVE", "INACTIVE"]


# --------------------------------------------------------------------------- #
# detail / update / deactivate
# --------------------------------------------------------------------------- #


def test_document_template_detail_returns_404_for_unknown_public_id(auth_client, institution):
    response = auth_client.get(reverse("document-template-detail", args=[MISSING_UUID]))

    assert response.status_code == 404


def test_document_template_detail_returns_404_for_another_institution(auth_client, institution):
    foreign = DocumentTemplateFactory()  # different institution

    response = auth_client.get(reverse("document-template-detail", args=[foreign.public_id]))

    assert response.status_code == 404


def test_patch_document_template_updates_name(auth_client, institution):
    template = DocumentTemplateFactory(institution=institution, name="Old")

    response = auth_client.patch(
        reverse("document-template-detail", args=[template.public_id]),
        {"name": "New"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New"


def test_patch_document_template_does_not_accept_code(auth_client, institution):
    template = DocumentTemplateFactory(institution=institution, code="ORIGINAL")

    response = auth_client.patch(
        reverse("document-template-detail", args=[template.public_id]),
        {"code": "CHANGED"},
        content_type="application/json",
    )

    assert response.status_code == 200
    template.refresh_from_db()
    assert template.code == "ORIGINAL"


def test_delete_document_template_deactivates_instead_of_deleting(auth_client, institution):
    template = DocumentTemplateFactory(institution=institution)

    response = auth_client.delete(reverse("document-template-detail", args=[template.public_id]))

    assert response.status_code == 204
    template.refresh_from_db()
    assert template.is_active is False
    assert DocumentTemplate.objects.filter(pk=template.pk).exists()


# --------------------------------------------------------------------------- #
# versions (RF-PLA-005)
# --------------------------------------------------------------------------- #


@pytest.mark.security
def test_document_template_versions_endpoint_requires_authentication(client, institution):
    template = DocumentTemplateFactory(institution=institution)

    response = client.get(reverse("document-template-version-list", args=[template.public_id]))

    assert response.status_code in (401, 403)


def test_create_document_template_creates_its_first_version(auth_client, institution):
    create_response = auth_client.post(
        reverse("document-template-list-create"),
        {"name": "Constancia", "code": "CONST"},
        content_type="application/json",
    )
    public_id = create_response.json()["public_id"]

    response = auth_client.get(reverse("document-template-version-list", args=[public_id]))

    assert response.status_code == 200
    items = _items(response)
    assert len(items) == 1
    assert items[0]["sequence"] == 1
    assert items[0]["name"] == "Constancia"


def test_update_document_template_adds_a_new_version_most_recent_first(auth_client, institution):
    template = DocumentTemplateFactory(institution=institution, name="Old")
    DocumentTemplateVersionFactory(template=template, sequence=1, name="Old")

    auth_client.patch(
        reverse("document-template-detail", args=[template.public_id]),
        {"name": "New"},
        content_type="application/json",
    )

    response = auth_client.get(reverse("document-template-version-list", args=[template.public_id]))

    sequences = [item["sequence"] for item in _items(response)]
    assert sequences == [2, 1]


def test_document_template_versions_returns_404_for_another_institution(auth_client, institution):
    foreign = DocumentTemplateFactory()  # different institution

    response = auth_client.get(reverse("document-template-version-list", args=[foreign.public_id]))

    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# field tags
# --------------------------------------------------------------------------- #


def test_list_field_tags_returns_the_fixed_catalogue(auth_client):
    response = auth_client.get(reverse("document-field-tag-list"))

    assert response.status_code == 200
    codes = {item["code"] for item in _items(response)}
    assert codes == set(FIELD_TAG_CODES)
    assert all(item["sensitive"] is False for item in _items(response))


def test_list_document_types_returns_the_fixed_catalogue(auth_client):
    response = auth_client.get(reverse("document-type-list"))

    assert response.status_code == 200
    assert response.json()["results"] == [
        {"code": "certificate", "label": "Certificado"},
        {"code": "report", "label": "Reporte"},
        {"code": "other", "label": "Otro"},
    ]


def _grant_document_issue(user):
    permission = PermissionFactory(codename="document_issue")
    return RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


def _enrolment():
    section = SectionFactory()
    return create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )


def _eligibility(client, enrolment_id):
    return client.get(
        reverse("document-official-issuance-eligibility"), {"enrolment_id": str(enrolment_id)}
    )


def test_official_document_eligibility_allows_complete_enrolment(auth_client):
    enrolment = _enrolment()
    _grant_document_issue(auth_client.user)

    response = _eligibility(auth_client, enrolment.public_id)

    assert response.status_code == 200
    assert response.json() == {"eligible": True, "blocking_document_codes": []}


def test_official_document_eligibility_reports_pending_documents(auth_client):
    enrolment = _enrolment()
    set_document_requirement(enrolment=enrolment, code="BIRTH-CERT", name="Birth certificate")
    _grant_document_issue(auth_client.user)

    response = _eligibility(auth_client, enrolment.public_id)

    assert response.status_code == 200
    assert response.json() == {"eligible": False, "blocking_document_codes": ["BIRTH-CERT"]}
    assert AuditEvent.objects.filter(action="documents.official_issuance.blocked").exists()


def test_official_document_eligibility_returns_404_for_unknown_enrolment(auth_client):
    _grant_document_issue(auth_client.user)

    response = _eligibility(auth_client, MISSING_UUID)

    assert response.status_code == 404


@pytest.mark.security
def test_official_document_eligibility_requires_issue_permission(auth_client):
    enrolment = _enrolment()

    response = _eligibility(auth_client, enrolment.public_id)

    assert response.status_code == 403
    assert AuditEvent.objects.filter(action="documents.official_issuance.denied").exists()


def _historical_cycle_report(client, enrolment_id):
    return client.get(
        reverse("document-historical-cycle-report"), {"enrolment_id": str(enrolment_id)}
    )


def test_historical_cycle_report_is_generated_for_a_closed_cycle(auth_client):
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    close_academic_cycle(cycle=section.academic_cycle)
    _grant_document_issue(auth_client.user)

    response = _historical_cycle_report(auth_client, enrolment.public_id)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert b"Boleta" in response.content


def test_historical_cycle_report_rejects_an_open_cycle(auth_client):
    enrolment = _enrolment()
    _grant_document_issue(auth_client.user)

    response = _historical_cycle_report(auth_client, enrolment.public_id)

    assert response.status_code == 400
    assert "cerrado" in _detail(response)


def test_historical_cycle_report_returns_404_for_unknown_enrolment(auth_client):
    _grant_document_issue(auth_client.user)

    response = _historical_cycle_report(auth_client, MISSING_UUID)

    assert response.status_code == 404


@pytest.mark.security
def test_historical_cycle_report_requires_issue_permission(auth_client):
    enrolment = _enrolment()

    response = _historical_cycle_report(auth_client, enrolment.public_id)

    assert response.status_code == 403


def _compile_batch(client, **payload):
    return client.post(reverse("document-batch-compile"), payload, content_type="application/json")


def test_document_batch_compile_generates_report_for_whole_section(auth_client):
    section = SectionFactory()
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    close_academic_cycle(cycle=section.academic_cycle)
    _grant_document_issue(auth_client.user)

    response = _compile_batch(auth_client, section_id=str(section.public_id))

    assert response.status_code == 200
    assert response.json() == {"count": 1, "replayed": False}


def test_document_batch_compile_requires_section_or_grade(auth_client):
    _grant_document_issue(auth_client.user)

    response = _compile_batch(auth_client)

    assert response.status_code == 400


def test_document_batch_compile_requires_issue_permission(auth_client):
    section = SectionFactory()

    response = _compile_batch(auth_client, section_id=str(section.public_id))

    assert response.status_code == 403


def test_document_batch_compile_is_idempotent_via_client_batch_id(auth_client):
    section = SectionFactory()
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    close_academic_cycle(cycle=section.academic_cycle)
    _grant_document_issue(auth_client.user)

    first = _compile_batch(
        auth_client, section_id=str(section.public_id), client_batch_id="retry-abc"
    )
    second = _compile_batch(
        auth_client, section_id=str(section.public_id), client_batch_id="retry-abc"
    )

    assert first.json() == {"count": 1, "replayed": False}
    assert second.json() == {"count": 1, "replayed": True}


def test_document_verification_is_public_and_confirms_a_genuine_code(client):
    """RF-EMI-009: no authentication required, per the issue's own acceptance criteria."""
    template = DocumentTemplateFactory()
    generated = compile_generated_document(
        template=template, payload={"document_type": "Certificado"}
    )

    response = client.get(reverse("document-verify", args=[generated.verification_code]))

    assert response.status_code == 200
    assert response.json() == {
        "valid": True,
        "document_type": "Certificado",
        "issued_at": generated.issued_at,
    }


def test_document_verification_rejects_an_unknown_code(client):
    response = client.get(reverse("document-verify", args=["does-not-exist"]))

    assert response.status_code == 200
    assert response.json() == {"valid": False}


def test_official_document_eligibility_allows_superuser_without_role(client):
    enrolment = _enrolment()
    client.force_login(UserFactory(is_superuser=True))

    response = _eligibility(client, enrolment.public_id)

    assert response.status_code == 200
    assert response.json() == {"eligible": True, "blocking_document_codes": []}


def test_include_sensitive_field_tags_without_permission_returns_403(auth_client):
    response = auth_client.get(reverse("document-field-tag-list"), {"include_sensitive": "true"})

    assert response.status_code == 403


def test_include_sensitive_field_tags_with_permission_returns_200(auth_client):
    permission = PermissionFactory(codename="student_view_sensitive")
    RoleAssignmentFactory(user=auth_client.user, role=RoleFactory(permissions=[permission]))

    response = auth_client.get(reverse("document-field-tag-list"), {"include_sensitive": "true"})

    assert response.status_code == 200
    codes = {item["code"] for item in _items(response)}
    assert codes == set(FIELD_TAG_CODES)
