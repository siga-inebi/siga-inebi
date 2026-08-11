import pytest
from django.urls import reverse

from apps.documents.field_catalog import FIELD_TAG_CODES
from apps.documents.models import DocumentTemplate
from tests.factories.documents import DocumentTemplateFactory
from tests.factories.identity import PermissionFactory, RoleAssignmentFactory, RoleFactory

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
# field tags
# --------------------------------------------------------------------------- #


def test_list_field_tags_returns_the_fixed_catalogue(auth_client):
    response = auth_client.get(reverse("document-field-tag-list"))

    assert response.status_code == 200
    codes = {item["code"] for item in _items(response)}
    assert codes == set(FIELD_TAG_CODES)
    assert all(item["sensitive"] is False for item in _items(response))


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
