import pytest
from django.urls import reverse

from apps.academics.models import Campus
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    GradeOfferingFactory,
    ShiftFactory,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]

MISSING_UUID = "00000000-0000-0000-0000-000000000000"


def _detail(response):
    return response.json()["error"]["detail"]


def _items(response):
    """Rows of a paginated list response."""
    return response.json()["results"]


# --------------------------------------------------------------------------- #
# authentication
# --------------------------------------------------------------------------- #


@pytest.mark.security
@pytest.mark.parametrize(
    "url_name",
    ["campus-list-create"],
)
def test_catalog_endpoints_require_authentication(client, url_name):
    response = client.get(reverse(url_name))

    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------- #
# campuses
# --------------------------------------------------------------------------- #


def test_create_campus_returns_201_with_public_id(auth_client, institution):
    response = auth_client.post(
        reverse("campus-list-create"),
        {"name": "Sede Central", "code": "central", "address": "Zona 1", "is_main": True},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "CENTRAL"
    assert body["is_main"] is True
    assert "public_id" in body
    assert Campus.objects.filter(institution=institution, code="CENTRAL").exists()


def test_create_campus_rejects_duplicate_code_with_400(auth_client, institution):
    CampusFactory(institution=institution, code="CENTRAL")

    response = auth_client.post(
        reverse("campus-list-create"),
        {"name": "Otra", "code": "CENTRAL"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "already" in str(_detail(response))


def test_create_campus_rejects_missing_code_with_field_error(auth_client, institution):
    response = auth_client.post(
        reverse("campus-list-create"),
        {"name": "Sede sin codigo"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "code" in _detail(response)


def test_list_campuses_only_returns_current_institution(auth_client, institution):
    CampusFactory(institution=institution, code="CENTRAL")
    CampusFactory(code="OTHER")  # another institution

    response = auth_client.get(reverse("campus-list-create"))

    assert response.status_code == 200
    codes = [item["code"] for item in _items(response)]
    assert codes == ["CENTRAL"]


def test_list_campuses_hides_inactive_by_default_and_shows_them_on_request(
    auth_client, institution
):
    CampusFactory(institution=institution, code="ACTIVE")
    CampusFactory(institution=institution, code="OLD", is_active=False)

    default = auth_client.get(reverse("campus-list-create"))
    included = auth_client.get(reverse("campus-list-create"), {"include_inactive": "true"})

    assert [item["code"] for item in _items(default)] == ["ACTIVE"]
    assert sorted(item["code"] for item in _items(included)) == ["ACTIVE", "OLD"]


def test_campus_detail_returns_404_for_unknown_public_id(auth_client, institution):
    response = auth_client.get(reverse("campus-detail", args=[MISSING_UUID]))

    assert response.status_code == 404


def test_campus_detail_returns_404_for_another_institution(auth_client, institution):
    foreign = CampusFactory()

    response = auth_client.get(reverse("campus-detail", args=[foreign.public_id]))

    assert response.status_code == 404


def test_patch_campus_updates_name(auth_client, institution):
    campus = CampusFactory(institution=institution, name="Sede Vieja")

    response = auth_client.patch(
        reverse("campus-detail", args=[campus.public_id]),
        {"name": "Sede Nueva"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Sede Nueva"


def test_delete_campus_deactivates_instead_of_deleting(auth_client, institution):
    campus = CampusFactory(institution=institution)

    response = auth_client.delete(reverse("campus-detail", args=[campus.public_id]))

    assert response.status_code == 204
    campus.refresh_from_db()
    assert campus.is_active is False


def test_delete_campus_in_use_returns_400(auth_client, institution):
    campus = CampusFactory(institution=institution)
    shift = ShiftFactory(campus=campus)
    cycle = AcademicCycleFactory(institution=institution)
    GradeOfferingFactory(academic_cycle=cycle, shift=shift)

    response = auth_client.delete(reverse("campus-detail", args=[campus.public_id]))

    assert response.status_code == 400
    assert "active cycle" in str(_detail(response))


# --------------------------------------------------------------------------- #
# shifts (per campus)
# --------------------------------------------------------------------------- #


def test_create_shift_under_its_campus(auth_client, institution):
    campus = CampusFactory(institution=institution)

    response = auth_client.post(
        reverse("campus-shift-list-create", args=[campus.public_id]),
        {"name": "Matutina", "code": "mat"},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["code"] == "MAT"
    assert response.json()["campus"]["code"] == campus.code


def test_list_shifts_is_scoped_to_the_campus(auth_client, institution):
    campus = CampusFactory(institution=institution)
    ShiftFactory(campus=campus, code="MAT")
    ShiftFactory(campus=CampusFactory(institution=institution), code="VES")

    response = auth_client.get(reverse("campus-shift-list-create", args=[campus.public_id]))

    assert [item["code"] for item in _items(response)] == ["MAT"]


def test_create_shift_under_unknown_campus_returns_404(auth_client, institution):
    response = auth_client.post(
        reverse("campus-shift-list-create", args=[MISSING_UUID]),
        {"name": "Matutina", "code": "MAT"},
        content_type="application/json",
    )

    assert response.status_code == 404


def test_shift_detail_roundtrip(auth_client, institution):
    shift = ShiftFactory(campus=CampusFactory(institution=institution), name="Matutina")

    read = auth_client.get(reverse("shift-detail", args=[shift.public_id]))
    renamed = auth_client.patch(
        reverse("shift-detail", args=[shift.public_id]),
        {"name": "Jornada Matutina"},
        content_type="application/json",
    )
    removed = auth_client.delete(reverse("shift-detail", args=[shift.public_id]))

    assert read.json()["name"] == "Matutina"
    assert renamed.json()["name"] == "Jornada Matutina"
    assert removed.status_code == 204
    shift.refresh_from_db()
    assert shift.is_active is False


def test_shift_detail_of_another_institution_returns_404(auth_client, institution):
    foreign = ShiftFactory()

    response = auth_client.get(reverse("shift-detail", args=[foreign.public_id]))

    assert response.status_code == 404


def test_deactivate_shift_in_use_returns_400(auth_client, institution):
    shift = ShiftFactory(campus=CampusFactory(institution=institution))
    GradeOfferingFactory(academic_cycle=AcademicCycleFactory(institution=institution), shift=shift)

    response = auth_client.delete(reverse("shift-detail", args=[shift.public_id]))

    assert response.status_code == 400
    assert "active cycle" in str(_detail(response))
