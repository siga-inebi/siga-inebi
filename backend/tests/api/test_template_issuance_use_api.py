import pytest
from django.test import Client
from django.urls import reverse

from apps.documents.models import DocumentTemplate
from tests.factories.documents import DocumentTemplateFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def payload(code, **extra):
    return {"name": code, "code": code, "kind": "report", **extra}


def test_api_exposes_use_and_requires_exact_confirmation(admin_client, institution):
    url = reverse("document-template-list-create")
    first = admin_client.post(
        url, payload("FIRST", issuance_use="study_certificate"), content_type="application/json"
    )
    assert first.status_code == 201
    first_id = first.json()["public_id"]
    data = payload("NEXT", issuance_use="study_certificate")
    assert admin_client.post(url, data, content_type="application/json").status_code == 400
    data["replaces_template_id"] = first_id
    second = admin_client.post(url, data, content_type="application/json")
    assert second.status_code == 201
    assert second.json()["issuance_use"] == "study_certificate"
    assert not DocumentTemplate.objects.get(public_id=first_id).is_active
    versions = admin_client.get(reverse("document-template-version-list", args=[first_id]))
    assert versions.json()["results"][0]["issuance_use"] == "study_certificate"


@pytest.mark.parametrize(
    "field,value",
    [
        ("issuance_use", "unknown"),
        ("issuance_use", ""),
        ("issuance_use", None),
        ("replaces_template_id", "bad-uuid"),
    ],
)
def test_api_validates_use_and_confirmation(admin_client, field, value):
    response = admin_client.post(
        reverse("document-template-list-create"),
        payload("BAD", **{field: value}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert field in response.json()["error"]["detail"]


def test_no_scope_cannot_replace_or_deactivate_occupant(auth_client, institution):
    first = DocumentTemplateFactory(institution=institution, issuance_use="study_certificate")
    response = auth_client.post(
        reverse("document-template-list-create"),
        payload(
            "DENIED", issuance_use="study_certificate", replaces_template_id=str(first.public_id)
        ),
        content_type="application/json",
    )
    assert response.status_code == 403
    first.refresh_from_db()
    assert first.is_active


def test_availability_is_authenticated_unpaginated_and_institution_scoped(auth_client, institution):
    DocumentTemplateFactory(issuance_use="study_certificate")
    url = reverse("template-issuance-use-list")
    assert Client().get(url).status_code == 403
    response = auth_client.get(url)
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(row["active_template"] is None and row["uses_fallback"] for row in response.json())


def test_preview_substitutes_every_allowed_marker_including_whitespace(admin_client, institution):
    from apps.documents.field_catalog import FIELD_TAG_CODES

    template = DocumentTemplateFactory(
        institution=institution, content="\n".join("{{ " + code + " }}" for code in FIELD_TAG_CODES)
    )
    values = {code: f"sample-{index}" for index, code in enumerate(FIELD_TAG_CODES)}
    before = template.versions.count()
    response = admin_client.post(
        reverse("document-template-preview", args=[template.public_id]),
        {"payload": values},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["marker_count"] == len(FIELD_TAG_CODES)
    assert response.json()["content"] == "\n".join(values.values())
    assert template.versions.count() == before
