"""
Domain rules of the study plan (RF-EST-005) and the teaching assignment
(RF-EST-009).

The pair is what the two requirements hinge on: a section can only be taught
what its grade studies in that cycle, and a subject cannot leave the plan while
somebody is still teaching it.
"""

import datetime

import pytest

from apps.academics.models import AcademicCycle, CurriculumPlan, TeachingAssignment
from apps.academics.services import (
    add_curriculum_entry,
    assign_teacher,
    end_teaching_assignment,
    get_curriculum_entry,
    remove_curriculum_entry,
    update_curriculum_entry,
)
from apps.common.models import DomainError
from tests.factories.academic import (
    AcademicCycleFactory,
    CurriculumPlanFactory,
    GradeFactory,
    InstitutionFactory,
    SectionFactory,
    SubjectFactory,
)
from tests.factories.people import PersonFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

TODAY = datetime.date(2026, 3, 1)


def _planned_section(**section_kwargs):
    """
    A section whose grade already studies one subject in its cycle.

    Almost every assignment test needs this, because assigning a teacher to a
    subject outside the plan is refused on purpose.
    """
    section = SectionFactory(**section_kwargs)
    subject = SubjectFactory(institution=section.academic_cycle.institution)
    add_curriculum_entry(cycle=section.academic_cycle, grade=section.grade, subject=subject)
    return section, subject


# --------------------------------------------------------------------------- #
# add_curriculum_entry
# --------------------------------------------------------------------------- #


def test_add_curriculum_entry_puts_a_subject_in_the_plan_of_a_grade():
    cycle = AcademicCycleFactory()
    grade = GradeFactory(institution=cycle.institution)
    subject = SubjectFactory(institution=cycle.institution)

    entry = add_curriculum_entry(cycle=cycle, grade=grade, subject=subject)

    assert entry.is_required is True
    assert entry.institution == cycle.institution


def test_a_subject_can_be_planned_as_optional():
    cycle = AcademicCycleFactory()

    entry = add_curriculum_entry(
        cycle=cycle,
        grade=GradeFactory(institution=cycle.institution),
        subject=SubjectFactory(institution=cycle.institution),
        is_required=False,
    )

    assert entry.is_required is False


def test_the_same_subject_cannot_be_planned_twice_for_a_grade():
    entry = CurriculumPlanFactory()

    with pytest.raises(DomainError, match="already in the plan"):
        add_curriculum_entry(cycle=entry.academic_cycle, grade=entry.grade, subject=entry.subject)


def test_the_same_subject_can_be_planned_for_another_grade():
    entry = CurriculumPlanFactory()
    other_grade = GradeFactory(institution=entry.academic_cycle.institution)

    added = add_curriculum_entry(
        cycle=entry.academic_cycle, grade=other_grade, subject=entry.subject
    )

    assert added.pk != entry.pk


def test_the_same_pair_can_be_planned_again_in_another_cycle():
    """The plan is per cycle, so a new cycle starts from a clean sheet (RF-EST-013)."""
    entry = CurriculumPlanFactory()
    next_cycle = AcademicCycleFactory(institution=entry.academic_cycle.institution)

    added = add_curriculum_entry(cycle=next_cycle, grade=entry.grade, subject=entry.subject)

    assert added.academic_cycle == next_cycle


def test_add_curriculum_entry_rejects_an_inactive_subject():
    cycle = AcademicCycleFactory()
    subject = SubjectFactory(institution=cycle.institution, is_active=False)

    with pytest.raises(DomainError, match="inactive"):
        add_curriculum_entry(
            cycle=cycle, grade=GradeFactory(institution=cycle.institution), subject=subject
        )


def test_add_curriculum_entry_rejects_a_subject_from_another_institution():
    cycle = AcademicCycleFactory()

    with pytest.raises(DomainError, match="same institution"):
        add_curriculum_entry(
            cycle=cycle,
            grade=GradeFactory(institution=cycle.institution),
            subject=SubjectFactory(institution=InstitutionFactory()),
        )


def test_add_curriculum_entry_rejects_a_grade_from_another_institution():
    cycle = AcademicCycleFactory()

    with pytest.raises(DomainError, match="same institution"):
        add_curriculum_entry(
            cycle=cycle,
            grade=GradeFactory(institution=InstitutionFactory()),
            subject=SubjectFactory(institution=cycle.institution),
        )


def test_a_closed_cycle_accepts_no_plan_change():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)

    with pytest.raises(DomainError, match="closed"):
        add_curriculum_entry(
            cycle=cycle,
            grade=GradeFactory(institution=cycle.institution),
            subject=SubjectFactory(institution=cycle.institution),
        )


# --------------------------------------------------------------------------- #
# get / update / remove
# --------------------------------------------------------------------------- #


def test_get_curriculum_entry_reports_a_subject_outside_the_plan():
    cycle = AcademicCycleFactory()
    grade = GradeFactory(institution=cycle.institution)
    subject = SubjectFactory(institution=cycle.institution)

    with pytest.raises(DomainError, match="not in the plan"):
        get_curriculum_entry(cycle, grade, subject)


def test_update_curriculum_entry_turns_a_subject_optional():
    entry = CurriculumPlanFactory(is_required=True)

    update_curriculum_entry(entry=entry, is_required=False)
    entry.refresh_from_db()

    assert entry.is_required is False


def test_update_curriculum_entry_without_a_value_changes_nothing():
    entry = CurriculumPlanFactory(is_required=True)

    update_curriculum_entry(entry=entry)
    entry.refresh_from_db()

    assert entry.is_required is True


def test_remove_curriculum_entry_deletes_the_row():
    entry = CurriculumPlanFactory()

    remove_curriculum_entry(entry=entry)

    assert not CurriculumPlan.objects.filter(pk=entry.pk).exists()


def test_a_planned_subject_with_an_open_assignment_cannot_be_removed():
    section, subject = _planned_section()
    assign_teacher(section=section, subject=subject, teacher=PersonFactory())
    entry = get_curriculum_entry(section.academic_cycle, section.grade, subject)

    with pytest.raises(DomainError, match="open teaching assignment"):
        remove_curriculum_entry(entry=entry)


def test_the_subject_can_be_removed_once_the_assignment_is_closed():
    section, subject = _planned_section()
    assignment = assign_teacher(section=section, subject=subject, teacher=PersonFactory())
    end_teaching_assignment(assignment=assignment)
    entry = get_curriculum_entry(section.academic_cycle, section.grade, subject)

    remove_curriculum_entry(entry=entry)

    assert not CurriculumPlan.objects.filter(pk=entry.pk).exists()


# --------------------------------------------------------------------------- #
# assign_teacher
# --------------------------------------------------------------------------- #


def test_assign_teacher_defaults_to_an_open_assignment_starting_today():
    section, subject = _planned_section()

    assignment = assign_teacher(section=section, subject=subject, teacher=PersonFactory())

    assert assignment.is_open
    assert assignment.starts_on is not None
    assert assignment.academic_cycle == section.academic_cycle


def test_assign_teacher_accepts_an_explicit_start_date():
    section, subject = _planned_section()

    assignment = assign_teacher(
        section=section, subject=subject, teacher=PersonFactory(), starts_on=TODAY
    )

    assert assignment.starts_on == TODAY


def test_a_subject_outside_the_plan_cannot_be_assigned():
    """RF-EST-009: a section only gets taught what its grade studies."""
    section = SectionFactory()
    unplanned = SubjectFactory(institution=section.academic_cycle.institution)

    with pytest.raises(DomainError, match="not in the plan"):
        assign_teacher(section=section, subject=unplanned, teacher=PersonFactory())


def test_only_one_teacher_can_hold_a_subject_of_a_section():
    section, subject = _planned_section()
    assign_teacher(section=section, subject=subject, teacher=PersonFactory())

    with pytest.raises(DomainError, match="already has an assigned teacher"):
        assign_teacher(section=section, subject=subject, teacher=PersonFactory())


def test_the_slot_takes_a_new_teacher_once_the_previous_one_is_closed():
    section, subject = _planned_section()
    first = assign_teacher(section=section, subject=subject, teacher=PersonFactory())
    end_teaching_assignment(assignment=first)

    second = assign_teacher(section=section, subject=subject, teacher=PersonFactory())

    assert second.is_open
    assert TeachingAssignment.objects.filter(section=section, subject=subject).count() == 2


def test_assign_teacher_rejects_an_inactive_teacher():
    section, subject = _planned_section()

    with pytest.raises(DomainError, match="inactive"):
        assign_teacher(section=section, subject=subject, teacher=PersonFactory(is_active=False))


def test_assign_teacher_rejects_an_inactive_section():
    section, subject = _planned_section()
    section.is_active = False
    section.save(update_fields=["is_active"])

    with pytest.raises(DomainError, match="inactive"):
        assign_teacher(section=section, subject=subject, teacher=PersonFactory())


def test_a_closed_cycle_accepts_no_new_assignment():
    section, subject = _planned_section()
    cycle = section.academic_cycle
    cycle.status = AcademicCycle.CycleStatus.CLOSED
    cycle.save(update_fields=["status"])
    section.refresh_from_db()

    with pytest.raises(DomainError, match="closed"):
        assign_teacher(section=section, subject=subject, teacher=PersonFactory())


# --------------------------------------------------------------------------- #
# end_teaching_assignment
# --------------------------------------------------------------------------- #


def test_ending_an_assignment_keeps_the_row_as_history():
    section, subject = _planned_section()
    assignment = assign_teacher(
        section=section, subject=subject, teacher=PersonFactory(), starts_on=TODAY
    )

    end_teaching_assignment(assignment=assignment, ends_on=TODAY + datetime.timedelta(days=30))

    assert TeachingAssignment.objects.filter(pk=assignment.pk).exists()
    assert assignment.is_open is False


def test_ending_an_assignment_twice_is_harmless():
    section, subject = _planned_section()
    assignment = assign_teacher(section=section, subject=subject, teacher=PersonFactory())
    end_teaching_assignment(assignment=assignment)
    first_end = assignment.ends_on

    end_teaching_assignment(assignment=assignment, ends_on=TODAY)

    assert assignment.ends_on == first_end


def test_an_assignment_cannot_end_before_it_starts():
    section, subject = _planned_section()
    assignment = assign_teacher(
        section=section, subject=subject, teacher=PersonFactory(), starts_on=TODAY
    )

    with pytest.raises(DomainError, match="cannot end before"):
        end_teaching_assignment(assignment=assignment, ends_on=TODAY - datetime.timedelta(days=1))
