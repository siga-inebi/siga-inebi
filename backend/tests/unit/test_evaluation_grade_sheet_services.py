"""
Domain rules of the evaluation UX delivery of #631 (docs/ux-ui.md 2.11).

- resolve_capture_teacher (V8).
- bulk_register_unit_grades shared by CSV and grade sheet (V2).
- build_grade_sheet (V2).
- create_evaluation_unit with the recovery window (RF-EVC-003).
- assess_recovery_eligibility lists the failed subareas (V4).
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apps.academics.models import CurriculumPlan, TeachingAssignment
from apps.common.exceptions import DomainError
from apps.enrolments.services import create_enrolment
from apps.evaluation.models import EvaluationUnit, Grade
from apps.evaluation.services import (
    assess_recovery_eligibility,
    build_grade_sheet,
    bulk_register_unit_grades,
    create_evaluation_unit,
    register_unit_grade,
    resolve_capture_teacher,
)
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.evaluation import open_unit
from tests.factories.people import PersonFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

ATTENDANCE_SERVICE_PATH = "apps.attendance.services.compute_attendance_percentage"


def _world(*, students=2, assigned=True):
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory()
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=section.grade, subject=subject)
    enrolments = [
        create_enrolment(
            student=StudentFactory(), academic_cycle=cycle, grade=section.grade, section=section
        )
        for _ in range(students)
    ]
    teacher = PersonFactory()
    if assigned:
        TeachingAssignment.objects.create(
            academic_cycle=cycle,
            section=section,
            subject=subject,
            teacher=teacher,
            starts_on=cycle.starts_on,
        )
    return SimpleNamespace(
        cycle=cycle,
        section=section,
        subject=subject,
        unit=open_unit(cycle),
        enrolments=enrolments,
        teacher=teacher,
    )


class TestResolveCaptureTeacher:
    def test_explicit_teacher_wins(self):
        world = _world()
        other = PersonFactory()

        assert (
            resolve_capture_teacher(
                evaluation_unit=world.unit,
                section=world.section,
                subject=world.subject,
                teacher=other,
            )
            == other
        )

    def test_inferred_from_current_assignment(self):
        world = _world()

        assert (
            resolve_capture_teacher(
                evaluation_unit=world.unit, section=world.section, subject=world.subject
            )
            == world.teacher
        )

    def test_ended_assignment_does_not_count(self):
        world = _world()
        TeachingAssignment.objects.update(ends_on=world.cycle.starts_on)

        with pytest.raises(DomainError, match="no tiene docente asignado"):
            resolve_capture_teacher(
                evaluation_unit=world.unit, section=world.section, subject=world.subject
            )

    def test_register_unit_grade_infers_it(self):
        world = _world()

        grade = register_unit_grade(
            enrolment=world.enrolments[0],
            subject=world.subject,
            evaluation_unit=world.unit,
            teacher=None,
            value=70,
        )

        assert grade.value == 70


class TestSharedBulkCapture:
    def test_enrolment_ids_create_and_correct(self):
        world = _world()
        first, second = world.enrolments
        Grade.objects.create(
            enrolment=first, subject=world.subject, evaluation_unit=world.unit, value=40
        )

        result = bulk_register_unit_grades(
            evaluation_unit=world.unit,
            section=world.section,
            subject=world.subject,
            rows=[
                {"enrolment_id": first.public_id, "value": 60},
                {"enrolment_id": str(second.public_id), "value": 75},
            ],
        )

        assert (result.created, result.updated, result.errors) == (1, 1, [])
        assert Grade.objects.get(enrolment=first).value == 60

    def test_section_of_another_cycle_is_rejected(self):
        world = _world()
        foreign = SectionFactory(academic_cycle=AcademicCycleFactory())

        with pytest.raises(DomainError, match="no pertenece al ciclo"):
            bulk_register_unit_grades(
                evaluation_unit=world.unit,
                section=foreign,
                subject=world.subject,
                rows=[{"student_code": "X", "value": 1}],
            )

    def test_without_assignment_and_teacher_is_rejected(self):
        world = _world(assigned=False)

        with pytest.raises(DomainError, match="no tiene docente asignado"):
            bulk_register_unit_grades(
                evaluation_unit=world.unit,
                section=world.section,
                subject=world.subject,
                rows=[{"student_code": "X", "value": 1}],
            )

    @pytest.mark.parametrize(
        ("raw", "field"),
        [(True, "value"), (55.5, "value"), ("", "value"), (None, "value"), ("abc", "value")],
    )
    def test_invalid_values_are_row_errors(self, raw, field):
        world = _world(students=1)

        result = bulk_register_unit_grades(
            evaluation_unit=world.unit,
            section=world.section,
            subject=world.subject,
            rows=[{"enrolment_id": world.enrolments[0].public_id, "value": raw}],
        )

        assert result.errors[0]["field"] == field
        assert result.created == result.updated == 0
        assert not Grade.objects.exists()

    def test_whole_float_is_accepted(self):
        world = _world(students=1)

        result = bulk_register_unit_grades(
            evaluation_unit=world.unit,
            section=world.section,
            subject=world.subject,
            rows=[{"enrolment_id": world.enrolments[0].public_id, "value": 80.0}],
        )

        assert result.created == 1

    def test_row_without_identifier(self):
        world = _world(students=1)

        result = bulk_register_unit_grades(
            evaluation_unit=world.unit,
            section=world.section,
            subject=world.subject,
            rows=[{"value": 80}],
        )

        assert result.errors == [
            {
                "index": 0,
                "student_code": None,
                "field": "student_code",
                "message": "Indique el código del estudiante o la matrícula.",
            }
        ]


class TestGradeSheet:
    def test_rows_and_teacher(self):
        world = _world()
        Grade.objects.create(
            enrolment=world.enrolments[0],
            subject=world.subject,
            evaluation_unit=world.unit,
            value=88,
        )

        sheet = build_grade_sheet(
            evaluation_unit=world.unit, section=world.section, subject=world.subject
        )

        assert sheet["teacher"] == world.teacher
        assert sheet["window_open"] is True
        grades = {row["enrolment"].pk: row["grade"] for row in sheet["rows"]}
        assert grades[world.enrolments[0].pk].value == 88
        assert grades[world.enrolments[1].pk] is None

    def test_closed_unit_reports_window_closed(self):
        world = _world()
        world.unit.status = EvaluationUnit.UnitStatus.CLOSED

        sheet = build_grade_sheet(
            evaluation_unit=world.unit, section=world.section, subject=world.subject
        )

        assert sheet["window_open"] is False


class TestCreateUnitWithRecoveryWindow:
    def test_window_applied(self):
        cycle = AcademicCycleFactory()

        unit = create_evaluation_unit(
            academic_cycle=cycle,
            number=1,
            name="Unidad 1",
            starts_on=date(2026, 1, 15),
            ends_on=date(2026, 3, 15),
            capture_starts_on=date(2026, 1, 15),
            capture_ends_on=date(2026, 3, 20),
            recovery_starts_on=date(2026, 3, 21),
            recovery_ends_on=date(2026, 3, 28),
        )

        unit.refresh_from_db()
        assert unit.recovery_starts_on == date(2026, 3, 21)

    def test_invalid_window_leaves_no_unit(self):
        cycle = AcademicCycleFactory()

        with pytest.raises(DomainError):
            create_evaluation_unit(
                academic_cycle=cycle,
                number=1,
                name="Unidad 1",
                starts_on=date(2026, 1, 15),
                ends_on=date(2026, 3, 15),
                capture_starts_on=date(2026, 1, 15),
                capture_ends_on=date(2026, 3, 20),
                recovery_starts_on=date(2026, 3, 28),
                recovery_ends_on=date(2026, 3, 21),
            )

        assert not EvaluationUnit.objects.filter(academic_cycle=cycle).exists()


class TestFailedSubjectList:
    def test_lists_failed_subareas_with_final_grade(self):
        world = _world(students=1)
        passed = SubjectFactory(name="Biología")
        CurriculumPlan.objects.create(
            academic_cycle=world.cycle, grade=world.section.grade, subject=passed
        )
        enrolment = world.enrolments[0]
        register_unit_grade(
            enrolment=enrolment,
            subject=world.subject,
            evaluation_unit=world.unit,
            teacher=None,
            value=45,
        )
        register_unit_grade(
            enrolment=enrolment,
            subject=passed,
            evaluation_unit=world.unit,
            teacher=world.teacher,
            value=90,
        )

        with patch(ATTENDANCE_SERVICE_PATH, return_value=SimpleNamespace(percentage=90.0)):
            eligibility = assess_recovery_eligibility(enrolment)

        assert eligibility.failed_subjects == 1
        assert eligibility.failed_subject_list == [{"subject": world.subject, "final_grade": 45}]
