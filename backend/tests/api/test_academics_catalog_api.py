import pytest
from django.urls import reverse

from apps.academics.models import Campus, Grade, Level, Subject
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    ClassroomFactory,
    ClassScheduleBlockFactory,
    GradeFactory,
    GradeOfferingFactory,
    LevelFactory,
    LevelSubjectFactory,
    ShiftFactory,
    SubjectFactory,
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
    ["campus-list-create", "level-list-create", "subject-list-create"],
)
def test_catalog_endpoints_require_authentication(client, url_name):
    response = client.get(reverse(url_name))

    assert response.status_code in (401, 403)


@pytest.mark.security
@pytest.mark.parametrize(
    "url_name, build",
    [
        ("campus-detail", lambda institution: CampusFactory(institution=institution)),
        ("level-detail", lambda institution: LevelFactory(institution=institution)),
        ("grade-detail", lambda institution: GradeFactory(level__institution=institution)),
        ("subject-detail", lambda institution: SubjectFactory(institution=institution)),
    ],
    ids=["campus", "level", "grade", "subject"],
)
def test_catalog_detail_endpoints_require_authentication(client, institution, url_name, build):
    """
    RF-EST-012: desactivar (DELETE) es la via de baja de estos elementos, y
    comparte permission_classes con el resto del detalle, pero ningun test
    lo confirmaba para estos cuatro -- ni siquiera via GET.
    """
    instance = build(institution)

    response = client.get(reverse(url_name, args=[instance.public_id]))

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


def test_create_campus_without_code_generates_one(auth_client, institution):
    """El codigo dejo de ser obligatorio: el backend emite el siguiente."""
    response = auth_client.post(
        reverse("campus-list-create"),
        {"name": "Sede sin codigo"},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["code"] == "SED-01"


def test_campus_next_code_endpoint_offers_what_the_creation_would_use(auth_client, institution):
    """
    La sugerencia y el alta salen de la misma funcion.

    Si no coincidieran, el formulario mostraria un codigo y guardaria otro, que
    es peor que no mostrar nada.
    """
    suggested = auth_client.get(reverse("campus-next-code")).json()["code"]

    created = auth_client.post(
        reverse("campus-list-create"),
        {"name": "Sede Norte"},
        content_type="application/json",
    )

    assert created.status_code == 201
    assert created.json()["code"] == suggested


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
    assert "ciclo activo" in str(_detail(response))


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
    assert "ciclo activo" in str(_detail(response))


def test_shift_endpoints_require_authentication(client, institution):
    shift = ShiftFactory(campus=CampusFactory(institution=institution))

    list_response = client.get(reverse("campus-shift-list-create", args=[shift.campus.public_id]))
    detail_response = client.get(reverse("shift-detail", args=[shift.public_id]))

    assert list_response.status_code in (401, 403)
    assert detail_response.status_code in (401, 403)


# --------------------------------------------------------------------------- #
# classrooms (per campus) -- RF-AUL-001
# --------------------------------------------------------------------------- #


def test_create_classroom_under_its_campus(auth_client, institution):
    """Escenario 1 (#99): registrar un aula."""
    campus = CampusFactory(institution=institution)

    response = auth_client.post(
        reverse("campus-classroom-list-create", args=[campus.public_id]),
        {"name": "Aula 101", "code": "a-101", "location": "Edificio A, 1er nivel"},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "A-101"
    assert body["location"] == "Edificio A, 1er nivel"
    assert body["campus"]["code"] == campus.code


def test_create_classroom_rejects_duplicate_code_in_same_campus(auth_client, institution):
    """Escenario 2 (#99): rechazo por codigo duplicado en el mismo campus."""
    campus = CampusFactory(institution=institution)
    ClassroomFactory(campus=campus, code="A-101")

    response = auth_client.post(
        reverse("campus-classroom-list-create", args=[campus.public_id]),
        {"name": "Otra aula", "code": "A-101"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "already exists" in str(_detail(response))


def test_create_classroom_allows_same_code_in_a_different_campus(auth_client, institution):
    ClassroomFactory(campus=CampusFactory(institution=institution), code="A-101")
    other_campus = CampusFactory(institution=institution)

    response = auth_client.post(
        reverse("campus-classroom-list-create", args=[other_campus.public_id]),
        {"name": "Aula 101", "code": "A-101"},
        content_type="application/json",
    )

    assert response.status_code == 201


def test_list_classrooms_is_scoped_to_the_campus(auth_client, institution):
    campus = CampusFactory(institution=institution)
    ClassroomFactory(campus=campus, code="A-101")
    ClassroomFactory(campus=CampusFactory(institution=institution), code="A-201")

    response = auth_client.get(reverse("campus-classroom-list-create", args=[campus.public_id]))

    assert [item["code"] for item in _items(response)] == ["A-101"]


def test_create_classroom_under_unknown_campus_returns_404(auth_client, institution):
    response = auth_client.post(
        reverse("campus-classroom-list-create", args=[MISSING_UUID]),
        {"name": "Aula 101", "code": "A-101"},
        content_type="application/json",
    )

    assert response.status_code == 404


def test_classroom_detail_roundtrip(auth_client, institution):
    classroom = ClassroomFactory(
        campus=CampusFactory(institution=institution), name="Aula 101", location="Edificio A"
    )

    read = auth_client.get(reverse("classroom-detail", args=[classroom.public_id]))
    renamed = auth_client.patch(
        reverse("classroom-detail", args=[classroom.public_id]),
        {"name": "Aula Norte", "location": "Edificio B"},
        content_type="application/json",
    )
    removed = auth_client.delete(reverse("classroom-detail", args=[classroom.public_id]))

    assert read.json()["name"] == "Aula 101"
    assert renamed.json()["name"] == "Aula Norte"
    assert renamed.json()["location"] == "Edificio B"
    assert removed.status_code == 204
    classroom.refresh_from_db()
    assert classroom.is_active is False


def test_classroom_detail_of_another_institution_returns_404(auth_client, institution):
    foreign = ClassroomFactory()

    response = auth_client.get(reverse("classroom-detail", args=[foreign.public_id]))

    assert response.status_code == 404


def test_classroom_endpoints_require_authentication(client, institution):
    classroom = ClassroomFactory(campus=CampusFactory(institution=institution))

    list_response = client.get(
        reverse("campus-classroom-list-create", args=[classroom.campus.public_id])
    )
    detail_response = client.get(reverse("classroom-detail", args=[classroom.public_id]))

    assert list_response.status_code in (401, 403)
    assert detail_response.status_code in (401, 403)


# --------------------------------------------------------------------------- #
# schedule blocks (per shift) -- RF-HOR-001
# --------------------------------------------------------------------------- #


def test_create_schedule_block_under_its_shift(auth_client, institution):
    shift = ShiftFactory(campus=CampusFactory(institution=institution))

    response = auth_client.post(
        reverse("shift-schedule-block-list-create", args=[shift.public_id]),
        {"number": 1, "name": "Bloque 1", "starts_on": "07:00:00", "ends_on": "07:45:00"},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["number"] == 1
    assert response.json()["starts_on"] == "07:00:00"
    assert response.json()["shift"]["public_id"] == str(shift.public_id)


def test_create_schedule_block_rejects_overlap_with_400(auth_client, institution):
    shift = ShiftFactory(campus=CampusFactory(institution=institution))
    ClassScheduleBlockFactory(shift=shift, number=1)

    response = auth_client.post(
        reverse("shift-schedule-block-list-create", args=[shift.public_id]),
        {"number": 2, "name": "Bloque 2", "starts_on": "07:30:00", "ends_on": "08:15:00"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "se solapa" in str(_detail(response))


def test_list_schedule_blocks_is_scoped_to_the_shift_and_ordered_by_number(
    auth_client, institution
):
    shift = ShiftFactory(campus=CampusFactory(institution=institution))
    ClassScheduleBlockFactory(shift=shift, number=2, starts_on="08:00", ends_on="08:45")
    ClassScheduleBlockFactory(shift=shift, number=1, starts_on="07:00", ends_on="07:45")
    ClassScheduleBlockFactory(shift=ShiftFactory(campus=CampusFactory(institution=institution)))

    response = auth_client.get(reverse("shift-schedule-block-list-create", args=[shift.public_id]))

    assert [item["number"] for item in _items(response)] == [1, 2]


def test_create_schedule_block_under_unknown_shift_returns_404(auth_client, institution):
    response = auth_client.post(
        reverse("shift-schedule-block-list-create", args=[MISSING_UUID]),
        {"number": 1, "name": "Bloque 1", "starts_on": "07:00:00", "ends_on": "07:45:00"},
        content_type="application/json",
    )

    assert response.status_code == 404


def test_schedule_block_detail_roundtrip(auth_client, institution):
    campus = CampusFactory(institution=institution)
    block = ClassScheduleBlockFactory(shift=ShiftFactory(campus=campus))

    read = auth_client.get(reverse("schedule-block-detail", args=[block.public_id]))
    renamed = auth_client.patch(
        reverse("schedule-block-detail", args=[block.public_id]),
        {"name": "Primera hora"},
        content_type="application/json",
    )
    removed = auth_client.delete(reverse("schedule-block-detail", args=[block.public_id]))

    assert read.json()["name"] == block.name
    assert renamed.json()["name"] == "Primera hora"
    assert removed.status_code == 204
    block.refresh_from_db()
    assert block.is_active is False


def test_schedule_block_detail_of_another_institution_returns_404(auth_client, institution):
    foreign = ClassScheduleBlockFactory()

    response = auth_client.get(reverse("schedule-block-detail", args=[foreign.public_id]))

    assert response.status_code == 404


def test_schedule_block_endpoints_require_authentication(client, institution):
    campus = CampusFactory(institution=institution)
    block = ClassScheduleBlockFactory(shift=ShiftFactory(campus=campus))

    list_response = client.get(
        reverse("shift-schedule-block-list-create", args=[block.shift.public_id])
    )
    detail_response = client.get(reverse("schedule-block-detail", args=[block.public_id]))

    assert list_response.status_code in (401, 403)
    assert detail_response.status_code in (401, 403)


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
    assert "secuencia" in str(_detail(response))


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

    assert [item["code"] for item in _items(response)] == ["PRE", "PRI", "DIV"]


def test_level_payload_exposes_grade_count(auth_client, institution):
    level = LevelFactory(institution=institution)
    GradeFactory(level=level)
    GradeFactory(level=level)

    response = auth_client.get(reverse("level-detail", args=[level.public_id]))

    assert response.status_code == 200
    assert response.json()["grade_count"] == 2


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
    assert "secuencia" in str(_detail(response))


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

    assert [item["code"] for item in _items(response)] == ["A", "B"]


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
    assert "misma institucion" in str(_detail(response))


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
    assert _items(response)[0]["weekly_hours"] == 6


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


def test_level_subject_endpoints_require_authentication(client, institution):
    link = LevelSubjectFactory(level=LevelFactory(institution=institution))

    list_response = client.get(reverse("level-subject-list-create", args=[link.level.public_id]))
    detail_response = client.get(
        reverse("level-subject-detail", args=[link.level.public_id, link.subject.public_id])
    )

    assert list_response.status_code in (401, 403)
    assert detail_response.status_code in (401, 403)
