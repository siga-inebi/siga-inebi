"""
#631, PR 1 (AD2, AD3): asignaciones calculadas en el servidor.

Vista previa del clonado entre ciclos, alta por lotes, matriz sección × curso y
la consulta única de la asignación vigente.
"""

from datetime import date

import pytest

from apps.academics import queries
from apps.academics.models import AcademicCycle, CurriculumPlan, Subject, TeachingAssignment
from apps.academics.services import create_teaching_assignments_batch
from apps.audit.models import AuditEvent
from apps.common.exceptions import DomainError
from apps.common.listing import descending_too, search_and_order
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    GradeFactory,
    InstitutionFactory,
    SectionFactory,
    ShiftFactory,
    SubjectFactory,
)
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _cycle(institution, year, status=AcademicCycle.CycleStatus.ACTIVE):
    return AcademicCycleFactory(
        institution=institution,
        year=year,
        name=f"Ciclo {year}",
        starts_on=date(year, 1, 15),
        ends_on=date(year, 10, 31),
        status=status,
    )


def _assign(cycle, section, subject, teacher=None, **kwargs):
    return TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=(teacher or TeacherFactory()).person,
        starts_on=kwargs.pop("starts_on", cycle.starts_on),
        **kwargs,
    )


@pytest.fixture
def two_cycles():
    institution = InstitutionFactory()
    grade = GradeFactory(institution=institution, name="Primero Básico")
    shift = ShiftFactory(campus=CampusFactory(institution=institution))
    source = _cycle(institution, 2031)
    target = _cycle(institution, 2032, status=AcademicCycle.CycleStatus.DRAFT)
    return institution, grade, shift, source, target


def test_clone_preview_matches_sections_by_grade_shift_and_name(two_cycles):
    institution, grade, shift, source, target = two_cycles
    math = SubjectFactory(institution=institution, name="Matemática")
    art = SubjectFactory(institution=institution, name="Arte")
    language = SubjectFactory(institution=institution, name="Lenguaje")
    source_a = SectionFactory(academic_cycle=source, grade=grade, shift=shift, name="A")
    source_b = SectionFactory(academic_cycle=source, grade=grade, shift=shift, name="B")
    target_a = SectionFactory(academic_cycle=target, grade=grade, shift=shift, name="A")
    teacher = TeacherFactory()
    _assign(source, source_a, math, teacher)
    _assign(source, source_a, art)
    _assign(source, source_b, math)
    # Finished assignments are history, never cloned.
    _assign(source, source_a, language, ends_on=date(2031, 3, 1))
    _assign(target, target_a, art)

    preview = queries.teaching_assignment_clone_preview(source_cycle=source, target_cycle=target)

    rows = {(row["section"].name, row["subject"].name): row for row in preview["rows"]}
    assert set(rows) == {("A", "Matemática"), ("A", "Arte"), ("B", "Matemática")}
    assert rows[("A", "Matemática")]["status"] == "pending"
    assert rows[("A", "Matemática")]["target_section"] == target_a
    assert rows[("A", "Matemática")]["teacher"] == teacher.person
    assert rows[("A", "Arte")]["status"] == "already_assigned"
    assert rows[("B", "Matemática")]["status"] == "unmatched"
    assert rows[("B", "Matemática")]["target_section"] is None
    assert preview["summary"] == {
        "total": 3,
        "pending": 1,
        "already_assigned": 1,
        "unmatched": 1,
    }
    assert preview["suggested_starts_on"] == target.starts_on


def test_clone_preview_ignores_inactive_target_sections(two_cycles):
    institution, grade, shift, source, target = two_cycles
    subject = SubjectFactory(institution=institution)
    _assign(
        source, SectionFactory(academic_cycle=source, grade=grade, shift=shift, name="A"), subject
    )
    SectionFactory(academic_cycle=target, grade=grade, shift=shift, name="A", is_active=False)

    preview = queries.teaching_assignment_clone_preview(source_cycle=source, target_cycle=target)

    assert preview["rows"][0]["status"] == "unmatched"


def test_batch_creates_valid_items_and_reports_rejected_ones(two_cycles):
    institution, grade, shift, source, _target = two_cycles
    section = SectionFactory(academic_cycle=source, grade=grade, shift=shift)
    math = SubjectFactory(institution=institution)
    art = SubjectFactory(institution=institution)
    teacher = TeacherFactory()
    _assign(source, section, art)
    foreign_section = SectionFactory()

    created, failed = create_teaching_assignments_batch(
        academic_cycle=source,
        items=[
            {
                "section_id": section.public_id,
                "subject_id": math.public_id,
                "teacher_id": teacher.public_id,
            },
            {
                "section_id": section.public_id,
                "subject_id": art.public_id,
                "teacher_id": teacher.public_id,
            },
            {
                "section_id": foreign_section.public_id,
                "subject_id": math.public_id,
                "teacher_id": teacher.public_id,
            },
        ],
        starts_on=date(2031, 2, 1),
    )

    assert [(a.section, a.subject, a.starts_on) for a in created] == [
        (section, math, date(2031, 2, 1))
    ]
    assert [failure["index"] for failure in failed] == [1, 2]
    assert failed[1]["detail"] == "La seccion debe pertenecer al ciclo escolar."
    assert AuditEvent.objects.filter(action="academics.teaching_assignment.created").count() == 1
    assert TeachingAssignment.objects.filter(academic_cycle=source, subject=math).count() == 1


def test_batch_rejects_an_empty_request(two_cycles):
    *_rest, source, _target = two_cycles

    with pytest.raises(DomainError, match="al menos una"):
        create_teaching_assignments_batch(academic_cycle=source, items=[])


def test_assignment_matrix_rows_follow_the_grade_curriculum_plan(two_cycles):
    institution, grade, shift, source, _target = two_cycles
    section = SectionFactory(academic_cycle=source, grade=grade, shift=shift, name="A")
    other_grade = GradeFactory(institution=institution)
    other_section = SectionFactory(academic_cycle=source, grade=other_grade, shift=shift)
    math = SubjectFactory(institution=institution, name="Matemática")
    art = SubjectFactory(institution=institution, name="Arte")
    for subject in (math, art):
        CurriculumPlan.objects.create(academic_cycle=source, grade=grade, subject=subject)
    assignment = _assign(source, section, math)

    sections = queries.assignment_matrix_sections(source, grade=grade)
    rows = queries.assignment_matrix_rows(source, sections)

    assert [row["section"] for row in rows] == [section]
    assert [(cell["subject"], cell["assignment"]) for cell in rows[0]["cells"]] == [
        (art, None),
        (math, assignment),
    ]
    all_rows = queries.assignment_matrix_rows(source, queries.assignment_matrix_sections(source))
    assert {row["section"] for row in all_rows} == {section, other_section}


def test_current_teaching_assignment_ignores_finished_ones(two_cycles):
    institution, grade, shift, source, _target = two_cycles
    section = SectionFactory(academic_cycle=source, grade=grade, shift=shift)
    subject = SubjectFactory(institution=institution)
    _assign(source, section, subject, starts_on=date(2031, 1, 15), ends_on=date(2031, 4, 30))

    assert (
        queries.current_teaching_assignment(academic_cycle=source, section=section, subject=subject)
        is None
    )

    current = _assign(source, section, subject, starts_on=date(2031, 5, 1))
    assert (
        queries.current_teaching_assignment(academic_cycle=source, section=section, subject=subject)
        == current
    )


def test_teaching_assignments_filters_current_and_section(two_cycles):
    institution, grade, shift, source, _target = two_cycles
    section = SectionFactory(academic_cycle=source, grade=grade, shift=shift)
    subject = SubjectFactory(institution=institution)
    finished = _assign(
        source, section, subject, starts_on=date(2031, 1, 15), ends_on=date(2031, 4, 30)
    )
    current = _assign(source, section, subject, starts_on=date(2031, 5, 1))
    _assign(source, SectionFactory(academic_cycle=source, grade=grade, shift=shift), subject)

    assert list(queries.teaching_assignments(institution, section=section, current=True)) == [
        current
    ]
    assert list(queries.teaching_assignments(institution, section=section, current=False)) == [
        finished
    ]


# --------------------------------------------------------------------------- #
# apps.common.listing
# --------------------------------------------------------------------------- #


def test_search_and_order_matches_any_field_and_whitelisted_order():
    institution = InstitutionFactory()
    SubjectFactory(institution=institution, name="Matemática", code="MAT")
    SubjectFactory(institution=institution, name="Arte", code="ART")
    SubjectFactory(institution=institution, name="Química", code="QMAT")
    queryset = Subject.objects.filter(institution=institution)
    orderings = descending_too({"name": ("name",)})

    found = search_and_order(
        queryset,
        search=" mat ",
        ordering="-name",
        search_fields=("name", "code"),
        orderings=orderings,
    )

    assert [subject.name for subject in found] == ["Química", "Matemática"]


def test_search_and_order_ignores_unknown_ordering_and_blank_search():
    institution = InstitutionFactory()
    SubjectFactory(institution=institution, name="B")
    SubjectFactory(institution=institution, name="A")
    queryset = Subject.objects.filter(institution=institution).order_by("name")

    result = search_and_order(
        queryset,
        search="  ",
        ordering="password",
        search_fields=("name",),
        orderings={"name": ("name",)},
    )

    assert [subject.name for subject in result] == ["A", "B"]


def test_descending_too_mirrors_every_field():
    assert descending_too({"grade": ("grade__sequence", "-name")}) == {
        "grade": ("grade__sequence", "-name"),
        "-grade": ("-grade__sequence", "name"),
    }
