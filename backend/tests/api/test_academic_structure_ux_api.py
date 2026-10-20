"""
#631, PR 1: contratos HTTP de estructura y asignaciones.

- AD2/AD4: listado de asignaciones con filtros y nombres, vista previa del
  clonado y alta por lotes calculados en el servidor.
- AD3: matriz sección × curso.
- S3: docente y aula con nombre en sesiones de clase; aula habitual en secciones.
- 1.2.1/A1/N1: catálogos editables sin max-age (se revalidan con ETag).
- Búsqueda y orden comunes en los catálogos.
"""

from datetime import date

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.academics.models import AcademicCycle, CurriculumPlan, TeachingAssignment
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    ClassroomFactory,
    ClassScheduleBlockFactory,
    ClassSessionFactory,
    GradeFactory,
    GradeOfferingFactory,
    LevelFactory,
    SectionFactory,
    ShiftFactory,
    SubjectFactory,
)
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _cycle(institution, year, status=AcademicCycle.CycleStatus.ACTIVE):
    return AcademicCycleFactory(
        institution=institution,
        year=year,
        name=f"Ciclo {year}",
        starts_on=date(year, 1, 15),
        ends_on=date(year, 10, 31),
        status=status,
    )


def _assign(cycle, section, subject, teacher, **kwargs):
    return TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
        starts_on=kwargs.pop("starts_on", cycle.starts_on),
        **kwargs,
    )


def _results(response):
    assert response.status_code == 200, response.content
    return response.json()["results"]


# --------------------------------------------------------------------------- #
# AD2/AD4: GET /academics/teaching-assignments/
# --------------------------------------------------------------------------- #


def test_teaching_assignment_list_filters_and_names(admin_client, institution):
    cycle = _cycle(institution, 2031)
    grade = GradeFactory(institution=institution, name="Primero Básico")
    section = SectionFactory(academic_cycle=cycle, grade=grade, name="A")
    other_section = SectionFactory(academic_cycle=cycle, grade=grade, name="B")
    subject = SubjectFactory(institution=institution, name="Matemática", code="MAT")
    teacher = TeacherFactory(person__first_name="Ana", person__last_name="López")
    _assign(cycle, section, subject, TeacherFactory(), ends_on=date(2031, 3, 31))
    current = _assign(cycle, section, subject, teacher, starts_on=date(2031, 4, 1))
    _assign(cycle, other_section, subject, TeacherFactory())

    rows = _results(
        admin_client.get(
            reverse("teaching-assignment-list-create"),
            {
                "academic_cycle_id": str(cycle.public_id),
                "section_id": str(section.public_id),
                "subject_id": str(subject.public_id),
                "current": "true",
            },
        )
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["public_id"] == str(current.public_id)
    assert row["section_id"] == str(section.public_id)
    assert row["teacher_id"] == str(teacher.public_id)
    assert row["section"] == {
        "public_id": str(section.public_id),
        "name": "A",
        "grade_name": "Primero Básico",
    }
    assert row["subject"] == {
        "public_id": str(subject.public_id),
        "name": "Matemática",
        "code": "MAT",
    }
    assert row["teacher"] == {"public_id": str(teacher.public_id), "name": "Ana López"}

    by_teacher = _results(
        admin_client.get(
            reverse("teaching-assignment-list-create"), {"teacher_id": str(teacher.public_id)}
        )
    )
    assert [item["public_id"] for item in by_teacher] == [str(current.public_id)]

    finished = _results(
        admin_client.get(
            reverse("teaching-assignment-list-create"),
            {"section_id": str(section.public_id), "current": "false"},
        )
    )
    assert len(finished) == 1
    assert finished[0]["ends_on"] == "2031-03-31"


def test_teaching_assignment_list_rejects_unknown_filter_ids(admin_client, institution):
    response = admin_client.get(
        reverse("teaching-assignment-list-create"),
        {"section_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 400


def test_teaching_assignment_list_has_constant_query_count(admin_client, institution):
    cycle = _cycle(institution, 2031)
    url = reverse("teaching-assignment-list-create")

    def count_queries():
        with CaptureQueriesContext(connection) as captured:
            assert admin_client.get(url).status_code == 200
        return len(captured)

    section = SectionFactory(academic_cycle=cycle)
    _assign(cycle, section, SubjectFactory(institution=institution), TeacherFactory())
    with_one = count_queries()
    for _ in range(4):
        _assign(
            cycle,
            SectionFactory(academic_cycle=cycle),
            SubjectFactory(institution=institution),
            TeacherFactory(),
        )

    assert count_queries() == with_one


def test_history_rows_also_carry_names(admin_client, institution):
    cycle = _cycle(institution, 2031)
    section = SectionFactory(academic_cycle=cycle)
    teacher = TeacherFactory()
    _assign(cycle, section, SubjectFactory(institution=institution), teacher)

    row = _results(admin_client.get(reverse("teaching-assignment-history")))[0]

    assert row["teacher"]["public_id"] == str(teacher.public_id)
    assert row["section"]["name"] == section.name


# --------------------------------------------------------------------------- #
# AD3: GET /academics/cycles/<id>/assignment-matrix/
# --------------------------------------------------------------------------- #


def test_assignment_matrix_contract(admin_client, institution):
    cycle = _cycle(institution, 2031)
    offering = GradeOfferingFactory(academic_cycle=cycle)
    section = SectionFactory(
        academic_cycle=cycle, grade=offering.grade, shift=offering.shift, name="A"
    )
    other_offering = GradeOfferingFactory(academic_cycle=cycle)
    SectionFactory(academic_cycle=cycle, grade=other_offering.grade, shift=other_offering.shift)
    math = SubjectFactory(institution=institution, name="Matemática")
    art = SubjectFactory(institution=institution, name="Arte")
    for subject in (math, art):
        CurriculumPlan.objects.create(academic_cycle=cycle, grade=offering.grade, subject=subject)
    teacher = TeacherFactory(person__first_name="Luis", person__last_name="Pérez")
    assignment = _assign(cycle, section, math, teacher)

    response = admin_client.get(
        reverse("cycle-assignment-matrix", args=[cycle.public_id]),
        {"grade_id": str(offering.grade.public_id)},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["count"] == 1
    row = body["results"][0]
    assert row["section"] == {
        "public_id": str(section.public_id),
        "name": "A",
        "grade": {"public_id": str(offering.grade.public_id), "name": offering.grade.name},
        "shift": {"public_id": str(offering.shift.public_id), "name": offering.shift.name},
    }
    assert row["cells"] == [
        {"subject": {"public_id": str(art.public_id), "name": "Arte"}, "assignment": None},
        {
            "subject": {"public_id": str(math.public_id), "name": "Matemática"},
            "assignment": {
                "public_id": str(assignment.public_id),
                "teacher": {"public_id": str(teacher.public_id), "name": "Luis Pérez"},
                "starts_on": "2031-01-15",
            },
        },
    ]

    everything = admin_client.get(reverse("cycle-assignment-matrix", args=[cycle.public_id]))
    assert everything.json()["count"] == 2


# --------------------------------------------------------------------------- #
# AD2: clone preview + batch
# --------------------------------------------------------------------------- #


def test_clone_preview_and_batch_apply(admin_client, institution):
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus=CampusFactory(institution=institution))
    source = _cycle(institution, 2031)
    target = _cycle(institution, 2032, status=AcademicCycle.CycleStatus.DRAFT)
    source_section = SectionFactory(academic_cycle=source, grade=grade, shift=shift, name="A")
    target_section = SectionFactory(academic_cycle=target, grade=grade, shift=shift, name="A")
    subject = SubjectFactory(institution=institution, name="Matemática")
    teacher = TeacherFactory()
    source_assignment = _assign(source, source_section, subject, teacher)

    preview = admin_client.get(
        reverse("cycle-teaching-assignment-clone-preview", args=[target.public_id]),
        {"source_cycle_id": str(source.public_id)},
    )

    assert preview.status_code == 200
    body = preview.json()
    assert body["source_cycle"] == {"public_id": str(source.public_id), "name": source.name}
    assert body["target_cycle"]["public_id"] == str(target.public_id)
    assert body["suggested_starts_on"] == "2032-01-15"
    assert body["summary"] == {"total": 1, "pending": 1, "already_assigned": 0, "unmatched": 0}
    row = body["results"][0]
    assert row["source_assignment_id"] == str(source_assignment.public_id)
    assert row["status"] == "pending"
    assert row["target_section"]["public_id"] == str(target_section.public_id)
    assert row["teacher"]["public_id"] == str(teacher.public_id)

    applied = admin_client.post(
        reverse("cycle-teaching-assignment-batch", args=[target.public_id]),
        {
            "starts_on": body["suggested_starts_on"],
            "items": [
                {
                    "section_id": row["target_section"]["public_id"],
                    "subject_id": row["subject"]["public_id"],
                    "teacher_id": row["teacher"]["public_id"],
                },
                {
                    "section_id": str(source_section.public_id),
                    "subject_id": row["subject"]["public_id"],
                    "teacher_id": row["teacher"]["public_id"],
                },
            ],
        },
        content_type="application/json",
    )

    assert applied.status_code == 201
    result = applied.json()
    assert len(result["created"]) == 1
    assert result["created"][0]["section"]["public_id"] == str(target_section.public_id)
    assert result["created"][0]["starts_on"] == "2032-01-15"
    assert result["failed"] == [
        {
            "index": 1,
            "section_id": str(source_section.public_id),
            "subject_id": str(subject.public_id),
            "teacher_id": str(teacher.public_id),
            "detail": "La seccion debe pertenecer al ciclo escolar.",
        }
    ]

    after = admin_client.get(
        reverse("cycle-teaching-assignment-clone-preview", args=[target.public_id]),
        {"source_cycle_id": str(source.public_id)},
    )
    assert after.json()["results"][0]["status"] == "already_assigned"


def test_clone_preview_requires_a_distinct_source(admin_client, institution):
    target = _cycle(institution, 2032, status=AcademicCycle.CycleStatus.DRAFT)
    url = reverse("cycle-teaching-assignment-clone-preview", args=[target.public_id])

    missing = admin_client.get(url)
    same = admin_client.get(url, {"source_cycle_id": str(target.public_id)})

    assert missing.status_code == 400
    assert same.status_code == 400


def test_clone_preview_rejects_source_from_another_institution(admin_client, institution):
    target = _cycle(institution, 2032, status=AcademicCycle.CycleStatus.DRAFT)
    foreign = AcademicCycleFactory(year=2031, starts_on=date(2031, 1, 15))

    response = admin_client.get(
        reverse("cycle-teaching-assignment-clone-preview", args=[target.public_id]),
        {"source_cycle_id": str(foreign.public_id)},
    )

    assert response.status_code == 400


def test_batch_validates_items(admin_client, institution):
    cycle = _cycle(institution, 2031)

    response = admin_client.post(
        reverse("cycle-teaching-assignment-batch", args=[cycle.public_id]),
        {"items": [{"section_id": "no-es-uuid"}]},
        content_type="application/json",
    )

    assert response.status_code == 400


# --------------------------------------------------------------------------- #
# S3: sesiones de clase y secciones con nombres
# --------------------------------------------------------------------------- #


def test_class_sessions_carry_teacher_and_classroom_names(admin_client, institution):
    cycle = _cycle(institution, 2031)
    section = SectionFactory(academic_cycle=cycle)
    classroom = ClassroomFactory(campus=section.offering.shift.campus, name="Laboratorio")
    teacher = TeacherFactory(person__first_name="Rosa", person__last_name="Díaz")
    with_teacher = ClassSessionFactory(section=section, classroom=classroom)
    _assign(cycle, section, with_teacher.subject, teacher)
    ClassSessionFactory(
        section=section,
        schedule_block=ClassScheduleBlockFactory(shift=section.offering.shift),
        day_of_week=2,
    )

    rows = _results(
        admin_client.get(reverse("section-class-session-list-create", args=[section.public_id]))
    )

    by_id = {row["public_id"]: row for row in rows}
    filled = by_id[str(with_teacher.public_id)]
    assert filled["teacher_id"] == str(teacher.public_id)
    assert filled["teacher"] == {"public_id": str(teacher.public_id), "name": "Rosa Díaz"}
    assert filled["classroom_id"] == str(classroom.public_id)
    assert filled["classroom"] == {"public_id": str(classroom.public_id), "name": "Laboratorio"}
    empty = next(row for key, row in by_id.items() if key != str(with_teacher.public_id))
    assert empty["teacher"] is None
    assert empty["teacher_id"] is None
    assert empty["classroom"] is None

    detail = admin_client.get(reverse("class-session-detail", args=[with_teacher.public_id]))
    assert detail.json()["teacher"]["name"] == "Rosa Díaz"


def test_class_session_teacher_does_not_cost_one_query_per_row(admin_client, institution):
    cycle = _cycle(institution, 2031)
    section = SectionFactory(academic_cycle=cycle)
    url = reverse("section-class-session-list-create", args=[section.public_id])

    def add_session(day):
        session = ClassSessionFactory(
            section=section,
            schedule_block=ClassScheduleBlockFactory(shift=section.offering.shift),
            day_of_week=day,
        )
        _assign(cycle, section, session.subject, TeacherFactory())

    def count_queries():
        with CaptureQueriesContext(connection) as captured:
            assert admin_client.get(url).status_code == 200
        return len(captured)

    add_session(1)
    with_one = count_queries()
    for day in (2, 3, 4):
        add_session(day)

    assert count_queries() == with_one


def test_section_carries_default_classroom_reference(admin_client, institution):
    cycle = _cycle(institution, 2031)
    section = SectionFactory(academic_cycle=cycle)
    classroom = ClassroomFactory(campus=section.offering.shift.campus, name="Aula 12")
    section.default_classroom = classroom
    section.save(update_fields=["default_classroom"])
    SectionFactory(academic_cycle=cycle)

    rows = _results(
        admin_client.get(
            reverse("section-list-create"), {"academic_cycle_id": str(cycle.public_id)}
        )
    )

    by_id = {row["public_id"]: row for row in rows}
    assert by_id[str(section.public_id)]["default_classroom"] == {
        "public_id": str(classroom.public_id),
        "name": "Aula 12",
    }
    assert by_id[str(section.public_id)]["default_classroom_id"] == str(classroom.public_id)
    assert all(
        row["default_classroom"] is None
        for key, row in by_id.items()
        if key != str(section.public_id)
    )


# --------------------------------------------------------------------------- #
# 1.2.1/A1/N1: caché de catálogos editables
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "route",
    ["campus-list-create", "level-list-create", "subject-list-create", "section-list-create"],
)
def test_editable_catalogues_always_revalidate(admin_client, institution, route):
    response = admin_client.get(reverse(route))

    cache_control = response.headers["Cache-Control"]
    assert "max-age=0" in cache_control
    assert "max-age=300" not in cache_control
    assert "private" in cache_control
    revalidated = admin_client.get(reverse(route), HTTP_IF_NONE_MATCH=response.headers["ETag"])
    assert revalidated.status_code == 304


def test_shift_catalogue_always_revalidates(admin_client, institution):
    campus = CampusFactory(institution=institution)

    response = admin_client.get(reverse("campus-shift-list-create", args=[campus.public_id]))

    assert "max-age=0" in response.headers["Cache-Control"]
    assert response.headers["ETag"]


def test_new_subject_shows_up_on_the_next_load(admin_client, institution):
    first = admin_client.get(reverse("subject-list-create"))
    SubjectFactory(institution=institution, name="Física")

    second = admin_client.get(
        reverse("subject-list-create"), HTTP_IF_NONE_MATCH=first.headers["ETag"]
    )

    assert second.status_code == 200
    assert [row["name"] for row in second.json()["results"]] == ["Física"]


# --------------------------------------------------------------------------- #
# búsqueda y orden comunes
# --------------------------------------------------------------------------- #


def _names(response, key="name"):
    return [row[key] for row in _results(response)]


def test_campus_search_and_ordering(admin_client, institution):
    CampusFactory(institution=institution, name="Central", code="CEN")
    CampusFactory(institution=institution, name="Norte", code="NOR")
    CampusFactory(institution=institution, name="Anexo central", code="ANX")
    url = reverse("campus-list-create")

    assert _names(admin_client.get(url, {"search": "central", "ordering": "-name"})) == [
        "Central",
        "Anexo central",
    ]
    assert _names(admin_client.get(url, {"search": "nor"})) == ["Norte"]
    assert _names(admin_client.get(url, {"ordering": "code"})) == [
        "Anexo central",
        "Central",
        "Norte",
    ]


def test_unknown_ordering_keeps_default_order(admin_client, institution):
    LevelFactory(institution=institution, name="Básico", sequence=2)
    LevelFactory(institution=institution, name="Primaria", sequence=1)

    response = admin_client.get(reverse("level-list-create"), {"ordering": "password"})

    assert _names(response) == ["Primaria", "Básico"]


def test_level_search_and_ordering_also_apply_to_expanded_grades(admin_client, institution):
    LevelFactory(institution=institution, name="Básico", code="BAS", sequence=2)
    LevelFactory(institution=institution, name="Primaria", code="PRI", sequence=1)

    response = admin_client.get(
        reverse("level-list-create"), {"expand": "grades", "ordering": "-sequence"}
    )
    searched = admin_client.get(reverse("level-list-create"), {"search": "bas"})

    assert _names(response) == ["Básico", "Primaria"]
    assert _names(searched) == ["Básico"]


def test_grade_classroom_and_shift_search(admin_client, institution):
    level = LevelFactory(institution=institution)
    GradeFactory(level=level, name="Primero", code="P1")
    GradeFactory(level=level, name="Segundo", code="P2")
    campus = CampusFactory(institution=institution)
    ClassroomFactory(campus=campus, name="Laboratorio", code="LAB")
    ClassroomFactory(campus=campus, name="Aula 1", code="A1")
    ShiftFactory(campus=campus, name="Matutina", code="MAT")
    ShiftFactory(campus=campus, name="Vespertina", code="VES")

    grades = admin_client.get(
        reverse("level-grade-list-create", args=[level.public_id]), {"search": "seg"}
    )
    classrooms = admin_client.get(
        reverse("classroom-list-create"), {"search": "lab", "include_inactive": "true"}
    )
    shifts = admin_client.get(
        reverse("campus-shift-list-create", args=[campus.public_id]), {"ordering": "-name"}
    )

    assert _names(grades) == ["Segundo"]
    assert _names(classrooms) == ["Laboratorio"]
    assert _names(shifts) == ["Vespertina", "Matutina"]


def test_subject_search_keeps_include_inactive(admin_client, institution):
    SubjectFactory(institution=institution, name="Matemática", code="MAT")
    SubjectFactory(institution=institution, name="Matemática II", code="MAT2", is_active=False)

    active = admin_client.get(reverse("subject-list-create"), {"search": "mat"})
    everything = admin_client.get(
        reverse("subject-list-create"), {"search": "mat", "include_inactive": "true"}
    )

    assert _names(active) == ["Matemática"]
    assert sorted(_names(everything)) == ["Matemática", "Matemática II"]


def test_section_and_curriculum_plan_search(admin_client, institution):
    cycle = _cycle(institution, 2031)
    first = GradeFactory(institution=institution, name="Primero Básico")
    second = GradeFactory(institution=institution, name="Segundo Básico")
    SectionFactory(academic_cycle=cycle, grade=first, name="A")
    SectionFactory(academic_cycle=cycle, grade=second, name="B")
    math = SubjectFactory(institution=institution, name="Matemática")
    art = SubjectFactory(institution=institution, name="Arte")
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=first, subject=math)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=first, subject=art)

    sections = admin_client.get(reverse("section-list-create"), {"search": "segundo"})
    plans = admin_client.get(
        reverse("curriculum-plan-list-create"), {"search": "primero", "ordering": "subject"}
    )

    assert _names(sections) == ["B"]
    assert [row["subject"]["name"] for row in _results(plans)] == ["Arte", "Matemática"]
