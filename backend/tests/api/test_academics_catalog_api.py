import pytest
from django.urls import reverse

from apps.academics.models import AcademicCycle, Campus, Grade, Level, Section, Subject
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    GradeFactory,
    GradeOfferingFactory,
    LevelFactory,
    LevelSubjectFactory,
    SectionFactory,
    ShiftFactory,
    SubjectFactory,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]

MISSING_UUID = "00000000-0000-0000-0000-000000000000"


def _detail(response):
    return response.json()["error"]["detail"]


# --------------------------------------------------------------------------- #
# authentication
# --------------------------------------------------------------------------- #


@pytest.mark.security
@pytest.mark.parametrize(
    "url_name",
    ["campus-list-create", "level-list-create", "subject-list-create"],
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
    codes = [item["code"] for item in response.json()]
    assert codes == ["CENTRAL"]


def test_list_campuses_hides_inactive_by_default_and_shows_them_on_request(
    auth_client, institution
):
    CampusFactory(institution=institution, code="ACTIVE")
    CampusFactory(institution=institution, code="OLD", is_active=False)

    default = auth_client.get(reverse("campus-list-create"))
    included = auth_client.get(reverse("campus-list-create"), {"include_inactive": "true"})

    assert [item["code"] for item in default.json()] == ["ACTIVE"]
    assert sorted(item["code"] for item in included.json()) == ["ACTIVE", "OLD"]


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

    assert [item["code"] for item in response.json()] == ["MAT"]


def test_create_shift_under_unknown_campus_returns_404(auth_client, institution):
    response = auth_client.post(
        reverse("campus-shift-list-create", args=[MISSING_UUID]),
        {"name": "Matutina", "code": "MAT"},
        content_type="application/json",
    )

    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# levels
# --------------------------------------------------------------------------- #


def test_create_level_returns_201(auth_client, institution):
    response = auth_client.post(
        reverse("level-list-create"),
        {"name": "Primaria", "code": "pri", "sequence": 2},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["code"] == "PRI"
    assert Level.objects.filter(institution=institution, sequence=2).exists()


def test_create_level_rejects_duplicate_sequence(auth_client, institution):
    LevelFactory(institution=institution, sequence=1)

    response = auth_client.post(
        reverse("level-list-create"),
        {"name": "Primaria", "code": "PRI", "sequence": 1},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "sequence" in str(_detail(response))


def test_create_level_rejects_non_positive_sequence_at_serializer(auth_client, institution):
    response = auth_client.post(
        reverse("level-list-create"),
        {"name": "Primaria", "code": "PRI", "sequence": 0},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "sequence" in _detail(response)


def test_list_levels_is_ordered_by_sequence(auth_client, institution):
    LevelFactory(institution=institution, code="DIV", sequence=4)
    LevelFactory(institution=institution, code="PRE", sequence=1)
    LevelFactory(institution=institution, code="PRI", sequence=2)

    response = auth_client.get(reverse("level-list-create"))

    assert [item["code"] for item in response.json()] == ["PRE", "PRI", "DIV"]


def test_level_payload_exposes_grade_count(auth_client, institution):
    level = LevelFactory(institution=institution)
    GradeFactory(level=level)
    GradeFactory(level=level)

    response = auth_client.get(reverse("level-detail", args=[level.public_id]))

    assert response.status_code == 200
    assert response.json()["grade_count"] == 2


# --------------------------------------------------------------------------- #
# grades (per level)
# --------------------------------------------------------------------------- #


def test_create_grade_under_its_level(auth_client, institution):
    level = LevelFactory(institution=institution)

    response = auth_client.post(
        reverse("level-grade-list-create", args=[level.public_id]),
        {"name": "Primero Primaria", "code": "pri1", "sequence": 1},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "PRI1"
    assert body["level"]["public_id"] == str(level.public_id)
    assert Grade.objects.filter(level=level, code="PRI1").exists()


def test_list_grades_of_a_level_is_ordered_by_sequence(auth_client, institution):
    level = LevelFactory(institution=institution)
    GradeFactory(level=level, code="B", sequence=2)
    GradeFactory(level=level, code="A", sequence=1)

    response = auth_client.get(reverse("level-grade-list-create", args=[level.public_id]))

    assert [item["code"] for item in response.json()] == ["A", "B"]


def test_create_grade_under_foreign_level_returns_404(auth_client, institution):
    foreign_level = LevelFactory()

    response = auth_client.post(
        reverse("level-grade-list-create", args=[foreign_level.public_id]),
        {"name": "Primero", "code": "PRI1", "sequence": 1},
        content_type="application/json",
    )

    assert response.status_code == 404


def test_delete_grade_deactivates_it(auth_client, institution):
    grade = GradeFactory(level=LevelFactory(institution=institution))

    response = auth_client.delete(reverse("grade-detail", args=[grade.public_id]))

    assert response.status_code == 204
    grade.refresh_from_db()
    assert grade.is_active is False


# --------------------------------------------------------------------------- #
# subjects and their link to levels
# --------------------------------------------------------------------------- #


def test_create_subject_returns_201(auth_client, institution):
    response = auth_client.post(
        reverse("subject-list-create"),
        {"name": "Matematica", "code": "mat"},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["code"] == "MAT"
    assert Subject.objects.filter(institution=institution, code="MAT").exists()


def test_subject_payload_lists_the_levels_it_is_taught_in(auth_client, institution):
    subject = SubjectFactory(institution=institution)
    primaria = LevelFactory(institution=institution, code="PRI", sequence=1)
    basico = LevelFactory(institution=institution, code="BAS", sequence=2)
    LevelSubjectFactory(level=primaria, subject=subject)
    LevelSubjectFactory(level=basico, subject=subject)

    response = auth_client.get(reverse("subject-detail", args=[subject.public_id]))

    assert response.status_code == 200
    assert [item["code"] for item in response.json()["levels"]] == ["PRI", "BAS"]


def test_link_subject_to_level(auth_client, institution):
    level = LevelFactory(institution=institution)
    subject = SubjectFactory(institution=institution)

    response = auth_client.post(
        reverse("level-subject-list-create", args=[level.public_id]),
        {"subject_id": str(subject.public_id), "weekly_hours": 5, "is_required": False},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["subject"]["code"] == subject.code
    assert body["weekly_hours"] == 5
    assert body["is_required"] is False


def test_link_subject_to_level_rejects_duplicate(auth_client, institution):
    link = LevelSubjectFactory(level=LevelFactory(institution=institution))

    response = auth_client.post(
        reverse("level-subject-list-create", args=[link.level.public_id]),
        {"subject_id": str(link.subject.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "already" in str(_detail(response))


def test_link_subject_from_another_institution_returns_400(auth_client, institution):
    level = LevelFactory(institution=institution)
    foreign_subject = SubjectFactory()

    response = auth_client.post(
        reverse("level-subject-list-create", args=[level.public_id]),
        {"subject_id": str(foreign_subject.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "institution" in str(_detail(response))


def test_link_unknown_subject_returns_400(auth_client, institution):
    level = LevelFactory(institution=institution)

    response = auth_client.post(
        reverse("level-subject-list-create", args=[level.public_id]),
        {"subject_id": MISSING_UUID},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_list_level_subjects_returns_curricular_metadata(auth_client, institution):
    level = LevelFactory(institution=institution)
    LevelSubjectFactory(level=level, weekly_hours=6, is_required=True)

    response = auth_client.get(reverse("level-subject-list-create", args=[level.public_id]))

    assert response.status_code == 200
    assert response.json()[0]["weekly_hours"] == 6


def test_patch_level_subject_updates_weekly_hours(auth_client, institution):
    link = LevelSubjectFactory(level=LevelFactory(institution=institution), weekly_hours=4)

    response = auth_client.patch(
        reverse("level-subject-detail", args=[link.level.public_id, link.subject.public_id]),
        {"weekly_hours": 8},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["weekly_hours"] == 8


def test_unlink_subject_from_level(auth_client, institution):
    link = LevelSubjectFactory(level=LevelFactory(institution=institution))

    response = auth_client.delete(
        reverse("level-subject-detail", args=[link.level.public_id, link.subject.public_id])
    )

    assert response.status_code == 204


def test_unlink_unlinked_subject_returns_400(auth_client, institution):
    level = LevelFactory(institution=institution)
    subject = SubjectFactory(institution=institution)

    response = auth_client.delete(
        reverse("level-subject-detail", args=[level.public_id, subject.public_id])
    )

    assert response.status_code == 400
    assert "not linked" in str(_detail(response))


# --------------------------------------------------------------------------- #
# grade offerings (the catalogue enrolments are assigned to)
# --------------------------------------------------------------------------- #


def test_create_offering_returns_201_with_denormalised_labels(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus=CampusFactory(institution=institution))

    response = auth_client.post(
        reverse("cycle-offering-list-create", args=[cycle.public_id]),
        {"grade_id": str(grade.public_id), "shift_id": str(shift.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["grade"]["code"] == grade.code
    assert body["shift"]["code"] == shift.code
    assert body["campus"]["code"] == shift.campus.code
    assert body["level"]["code"] == grade.level.code
    assert body["section_count"] == 0


def test_create_offering_in_closed_cycle_returns_400(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.CLOSED)
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus=CampusFactory(institution=institution))

    response = auth_client.post(
        reverse("cycle-offering-list-create", args=[cycle.public_id]),
        {"grade_id": str(grade.public_id), "shift_id": str(shift.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "closed" in str(_detail(response))


def test_create_offering_with_unknown_grade_returns_400(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    shift = ShiftFactory(campus=CampusFactory(institution=institution))

    response = auth_client.post(
        reverse("cycle-offering-list-create", args=[cycle.public_id]),
        {"grade_id": MISSING_UUID, "shift_id": str(shift.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_list_offerings_can_be_filtered_by_campus_and_level(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    central = CampusFactory(institution=institution, code="CENTRAL")
    annex = CampusFactory(institution=institution, code="ANEXO")
    primaria = LevelFactory(institution=institution, code="PRI", sequence=1)
    basico = LevelFactory(institution=institution, code="BAS", sequence=2)

    GradeOfferingFactory(
        academic_cycle=cycle,
        shift=ShiftFactory(campus=central),
        grade=GradeFactory(level=primaria),
    )
    GradeOfferingFactory(
        academic_cycle=cycle,
        shift=ShiftFactory(campus=annex),
        grade=GradeFactory(level=basico),
    )

    url = reverse("cycle-offering-list-create", args=[cycle.public_id])

    by_campus = auth_client.get(url, {"campus": str(central.public_id)})
    by_level = auth_client.get(url, {"level": str(basico.public_id)})

    assert len(by_campus.json()) == 1
    assert by_campus.json()[0]["campus"]["code"] == "CENTRAL"
    assert len(by_level.json()) == 1
    assert by_level.json()[0]["level"]["code"] == "BAS"


def test_list_offerings_with_unknown_filter_returns_empty_list(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    GradeOfferingFactory(academic_cycle=cycle)

    response = auth_client.get(
        reverse("cycle-offering-list-create", args=[cycle.public_id]),
        {"campus": MISSING_UUID},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_delete_offering_returns_204(auth_client, institution):
    offering = GradeOfferingFactory(academic_cycle=AcademicCycleFactory(institution=institution))

    response = auth_client.delete(reverse("offering-detail", args=[offering.public_id]))

    assert response.status_code == 204


def test_delete_offering_with_sections_returns_400(auth_client, institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))

    response = auth_client.delete(reverse("offering-detail", args=[section.offering.public_id]))

    assert response.status_code == 400
    assert "section" in str(_detail(response))


# --------------------------------------------------------------------------- #
# sections under an offering
# --------------------------------------------------------------------------- #


def test_create_section_under_offering(auth_client, institution):
    offering = GradeOfferingFactory(academic_cycle=AcademicCycleFactory(institution=institution))

    response = auth_client.post(
        reverse("offering-section-list-create", args=[offering.public_id]),
        {"name": "a", "capacity": 30},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "A"
    assert body["capacity"] == 30
    assert body["active_enrolment_count"] == 0
    assert Section.objects.filter(offering=offering, name="A").exists()


def test_create_section_rejects_negative_capacity_at_serializer(auth_client, institution):
    offering = GradeOfferingFactory(academic_cycle=AcademicCycleFactory(institution=institution))

    response = auth_client.post(
        reverse("offering-section-list-create", args=[offering.public_id]),
        {"name": "A", "capacity": -5},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "capacity" in _detail(response)


def test_section_list_reports_occupancy(auth_client, institution):
    from apps.enrolments.services import create_enrolment
    from tests.factories.students import StudentFactory

    section = SectionFactory(
        academic_cycle=AcademicCycleFactory(institution=institution), capacity=10
    )
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    response = auth_client.get(
        reverse("offering-section-list-create", args=[section.offering.public_id])
    )

    assert response.status_code == 200
    assert response.json()[0]["active_enrolment_count"] == 1
    assert response.json()[0]["available_seats"] == 9


def test_patch_section_capacity(auth_client, institution):
    section = SectionFactory(
        academic_cycle=AcademicCycleFactory(institution=institution), capacity=30
    )

    response = auth_client.patch(
        reverse("section-detail", args=[section.public_id]),
        {"capacity": 40},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["capacity"] == 40


def test_cycle_detail_still_lists_its_sections(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    SectionFactory(academic_cycle=cycle, name="A")

    response = auth_client.get(reverse("cycle-detail", args=[cycle.public_id]))

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["sections"]] == ["A"]


# --------------------------------------------------------------------------- #
# schema
# --------------------------------------------------------------------------- #


def test_openapi_schema_documents_the_catalogue_endpoints(auth_client):
    response = auth_client.get(reverse("schema"), {"format": "json"})

    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in [
        "/api/v1/academics/campuses/",
        "/api/v1/academics/campuses/{public_id}/shifts/",
        "/api/v1/academics/levels/",
        "/api/v1/academics/levels/{public_id}/grades/",
        "/api/v1/academics/levels/{public_id}/subjects/",
        "/api/v1/academics/subjects/",
        "/api/v1/academics/cycles/{cycle_public_id}/offerings/",
        "/api/v1/academics/offerings/{public_id}/sections/",
    ]:
        assert path in paths, f"missing documented path: {path}"


def test_openapi_operations_carry_summaries_and_tags(auth_client):
    response = auth_client.get(reverse("schema"), {"format": "json"})

    operations = response.json()["paths"]["/api/v1/academics/campuses/"]
    for method in ("get", "post"):
        assert operations[method]["summary"]
        assert operations[method]["tags"]


# --------------------------------------------------------------------------- #
# detail endpoints for the rest of the catalogue
# --------------------------------------------------------------------------- #


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


def test_grade_detail_roundtrip(auth_client, institution):
    grade = GradeFactory(level=LevelFactory(institution=institution), name="Primero")

    read = auth_client.get(reverse("grade-detail", args=[grade.public_id]))
    renamed = auth_client.patch(
        reverse("grade-detail", args=[grade.public_id]),
        {"name": "Primero Primaria", "sequence": 1},
        content_type="application/json",
    )

    assert read.json()["name"] == "Primero"
    assert renamed.json()["name"] == "Primero Primaria"
    assert renamed.json()["sequence"] == 1


def test_level_detail_patch_and_deactivate(auth_client, institution):
    level = LevelFactory(institution=institution, name="Basico", sequence=3)

    renamed = auth_client.patch(
        reverse("level-detail", args=[level.public_id]),
        {"name": "Ciclo Basico"},
        content_type="application/json",
    )
    removed = auth_client.delete(reverse("level-detail", args=[level.public_id]))

    assert renamed.json()["name"] == "Ciclo Basico"
    assert removed.status_code == 204
    level.refresh_from_db()
    assert level.is_active is False


def test_level_patch_with_taken_sequence_returns_400(auth_client, institution):
    LevelFactory(institution=institution, sequence=1)
    second = LevelFactory(institution=institution, sequence=2)

    response = auth_client.patch(
        reverse("level-detail", args=[second.public_id]),
        {"sequence": 1},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "sequence" in str(_detail(response))


def test_subject_detail_patch_and_deactivate(auth_client, institution):
    subject = SubjectFactory(institution=institution, name="Mate")

    renamed = auth_client.patch(
        reverse("subject-detail", args=[subject.public_id]),
        {"name": "Matematica"},
        content_type="application/json",
    )
    removed = auth_client.delete(reverse("subject-detail", args=[subject.public_id]))

    assert renamed.json()["name"] == "Matematica"
    assert removed.status_code == 204
    subject.refresh_from_db()
    assert subject.is_active is False


def test_cycle_create_open_and_close_roundtrip(auth_client, institution):
    created = auth_client.post(
        reverse("cycle-list-create"),
        {"name": "2027", "starts_on": "2027-01-15", "ends_on": "2027-10-30"},
        content_type="application/json",
    )
    assert created.status_code == 201
    assert created.json()["status"] == "draft"
    public_id = created.json()["public_id"]

    opened = auth_client.post(reverse("cycle-open", args=[public_id]))
    assert opened.json()["status"] == "active"

    closed = auth_client.post(reverse("cycle-close", args=[public_id]))
    assert closed.json()["status"] == "closed"

    reopened = auth_client.post(reverse("cycle-open", args=[public_id]))
    assert reopened.status_code == 400
    assert "closed" in str(_detail(reopened))


def test_cycle_create_rejects_end_before_start(auth_client, institution):
    response = auth_client.post(
        reverse("cycle-list-create"),
        {"name": "2027", "starts_on": "2027-10-30", "ends_on": "2027-01-15"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "ends_on" in _detail(response)


def test_cycle_list_only_returns_current_institution(auth_client, institution):
    AcademicCycleFactory(institution=institution, name="2026")
    AcademicCycleFactory(name="2026-other")

    response = auth_client.get(reverse("cycle-list-create"))

    assert [item["name"] for item in response.json()] == ["2026"]


def test_offering_detail_exposes_its_section_count(auth_client, institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))

    response = auth_client.get(reverse("offering-detail", args=[section.offering.public_id]))

    assert response.status_code == 200
    assert response.json()["section_count"] == 1


def test_section_detail_get_and_deactivate(auth_client, institution):
    section = SectionFactory(
        academic_cycle=AcademicCycleFactory(institution=institution), capacity=0
    )

    read = auth_client.get(reverse("section-detail", args=[section.public_id]))
    removed = auth_client.delete(reverse("section-detail", args=[section.public_id]))

    assert read.json()["available_seats"] is None
    assert removed.status_code == 204
    section.refresh_from_db()
    assert section.is_active is False


def test_section_detail_of_another_institution_returns_404(auth_client, institution):
    foreign = SectionFactory()

    response = auth_client.get(reverse("section-detail", args=[foreign.public_id]))

    assert response.status_code == 404


def test_patch_section_below_occupancy_returns_400(auth_client, institution):
    from apps.enrolments.services import create_enrolment
    from tests.factories.students import StudentFactory

    section = SectionFactory(
        academic_cycle=AcademicCycleFactory(institution=institution), capacity=5
    )
    for _ in range(2):
        create_enrolment(
            student=StudentFactory(),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
        )

    response = auth_client.patch(
        reverse("section-detail", args=[section.public_id]),
        {"capacity": 1},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "occupancy" in str(_detail(response))
