import pytest

from apps.academics.models import AcademicCycle, GradeOffering, Section
from apps.academics.services import (
    close_cycle,
    create_grade_offering,
    create_section,
    deactivate_section,
    remove_grade_offering,
    update_section,
)
from apps.common.models import DomainError
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    GradeFactory,
    GradeOfferingFactory,
    InstitutionFactory,
    LevelFactory,
    SectionFactory,
    ShiftFactory,
)
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _consistent(institution=None, cycle_status=AcademicCycle.CycleStatus.ACTIVE):
    """Build a cycle, a campus shift and a grade that all share one institution."""
    institution = institution or InstitutionFactory()
    cycle = AcademicCycleFactory(institution=institution, status=cycle_status)
    campus = CampusFactory(institution=institution)
    shift = ShiftFactory(campus=campus)
    grade = GradeFactory(institution=institution)
    return cycle, shift, grade


# --------------------------------------------------------------------------- #
# create_grade_offering  (grade + shift + campus + cycle)
# --------------------------------------------------------------------------- #


def test_create_grade_offering_links_grade_to_a_campus_shift():
    cycle, shift, grade = _consistent()

    offering = create_grade_offering(cycle=cycle, shift=shift, grade=grade)

    assert offering.academic_cycle == cycle
    assert offering.shift == shift
    assert offering.grade == grade
    assert offering.campus == shift.campus
    assert offering.level == grade.level


def test_the_same_grade_can_be_offered_in_two_shifts_of_one_campus():
    cycle, morning, grade = _consistent()
    afternoon = ShiftFactory(campus=morning.campus)

    create_grade_offering(cycle=cycle, shift=morning, grade=grade)
    create_grade_offering(cycle=cycle, shift=afternoon, grade=grade)

    assert GradeOffering.objects.filter(academic_cycle=cycle, grade=grade).count() == 2


def test_the_same_grade_and_shift_code_can_be_offered_in_two_campuses():
    institution = InstitutionFactory()
    cycle = AcademicCycleFactory(institution=institution)
    grade = GradeFactory(institution=institution)
    central = ShiftFactory(campus=CampusFactory(institution=institution), code="MAT")
    annex = ShiftFactory(campus=CampusFactory(institution=institution), code="MAT")

    create_grade_offering(cycle=cycle, shift=central, grade=grade)
    create_grade_offering(cycle=cycle, shift=annex, grade=grade)

    assert GradeOffering.objects.filter(academic_cycle=cycle, grade=grade).count() == 2


def test_create_grade_offering_rejects_duplicate_combination():
    cycle, shift, grade = _consistent()
    create_grade_offering(cycle=cycle, shift=shift, grade=grade)

    with pytest.raises(DomainError, match="already offered"):
        create_grade_offering(cycle=cycle, shift=shift, grade=grade)


def test_create_grade_offering_rejects_closed_cycle():
    cycle, shift, grade = _consistent(cycle_status=AcademicCycle.CycleStatus.CLOSED)

    with pytest.raises(DomainError, match="closed"):
        create_grade_offering(cycle=cycle, shift=shift, grade=grade)


def test_create_grade_offering_allows_draft_cycle():
    """The catalogue is built while the cycle is still a draft."""
    cycle, shift, grade = _consistent(cycle_status=AcademicCycle.CycleStatus.DRAFT)

    offering = create_grade_offering(cycle=cycle, shift=shift, grade=grade)

    assert offering.pk is not None


def test_create_grade_offering_rejects_shift_from_another_institution():
    cycle, _, grade = _consistent()
    foreign_shift = ShiftFactory()

    with pytest.raises(DomainError, match="institution"):
        create_grade_offering(cycle=cycle, shift=foreign_shift, grade=grade)


def test_create_grade_offering_rejects_grade_from_another_institution():
    cycle, shift, _ = _consistent()
    foreign_grade = GradeFactory()

    with pytest.raises(DomainError, match="institution"):
        create_grade_offering(cycle=cycle, shift=shift, grade=foreign_grade)


def test_create_grade_offering_rejects_inactive_shift():
    cycle, shift, grade = _consistent()
    shift.is_active = False
    shift.save(update_fields=["is_active"])

    with pytest.raises(DomainError, match="inactive"):
        create_grade_offering(cycle=cycle, shift=shift, grade=grade)


def test_create_grade_offering_rejects_inactive_campus():
    cycle, shift, grade = _consistent()
    shift.campus.is_active = False
    shift.campus.save(update_fields=["is_active"])

    with pytest.raises(DomainError, match="inactive"):
        create_grade_offering(cycle=cycle, shift=shift, grade=grade)


def test_create_grade_offering_rejects_inactive_grade():
    cycle, shift, grade = _consistent()
    grade.is_active = False
    grade.save(update_fields=["is_active"])

    with pytest.raises(DomainError, match="inactive"):
        create_grade_offering(cycle=cycle, shift=shift, grade=grade)


def test_create_grade_offering_rejects_inactive_level():
    cycle, shift, grade = _consistent()
    grade.level.is_active = False
    grade.level.save(update_fields=["is_active"])

    with pytest.raises(DomainError, match="inactive"):
        create_grade_offering(cycle=cycle, shift=shift, grade=grade)


def test_offerings_are_independent_between_cycles():
    """RF-EST-013: structure is versioned per cycle."""
    institution = InstitutionFactory()
    first = AcademicCycleFactory(institution=institution)
    second = AcademicCycleFactory(institution=institution)
    shift = ShiftFactory(campus=CampusFactory(institution=institution))
    grade = GradeFactory(institution=institution)

    create_grade_offering(cycle=first, shift=shift, grade=grade)
    create_grade_offering(cycle=second, shift=shift, grade=grade)

    assert GradeOffering.objects.filter(grade=grade).count() == 2


# --------------------------------------------------------------------------- #
# remove_grade_offering
# --------------------------------------------------------------------------- #


def test_remove_grade_offering_deletes_an_empty_offering():
    offering = GradeOfferingFactory()

    remove_grade_offering(offering=offering)

    assert GradeOffering.objects.filter(pk=offering.pk).exists() is False


def test_remove_grade_offering_rejects_offering_with_sections():
    section = SectionFactory()

    with pytest.raises(DomainError, match="section"):
        remove_grade_offering(offering=section.offering)


def test_remove_grade_offering_rejects_closed_cycle():
    offering = GradeOfferingFactory()
    close_cycle(cycle=offering.academic_cycle)
    offering.refresh_from_db()

    with pytest.raises(DomainError, match="closed"):
        remove_grade_offering(offering=offering)


# --------------------------------------------------------------------------- #
# create_section
# --------------------------------------------------------------------------- #


def test_create_section_hangs_from_the_offering():
    offering = GradeOfferingFactory()

    section = create_section(offering=offering, name="a", capacity=30)

    assert section.offering == offering
    assert section.name == "A"
    assert section.capacity == 30
    assert section.academic_cycle == offering.academic_cycle
    assert section.grade == offering.grade
    assert section.shift == offering.shift
    assert section.campus == offering.campus


def test_create_section_rejects_duplicate_name_in_same_offering():
    offering = GradeOfferingFactory()
    create_section(offering=offering, name="A", capacity=30)

    with pytest.raises(DomainError, match="already"):
        create_section(offering=offering, name="a", capacity=30)


def test_same_section_name_can_exist_in_two_shifts_of_the_same_grade():
    cycle, morning, grade = _consistent()
    afternoon = ShiftFactory(campus=morning.campus)
    morning_offering = create_grade_offering(cycle=cycle, shift=morning, grade=grade)
    afternoon_offering = create_grade_offering(cycle=cycle, shift=afternoon, grade=grade)

    create_section(offering=morning_offering, name="A", capacity=30)
    create_section(offering=afternoon_offering, name="A", capacity=30)

    assert Section.objects.filter(name="A", offering__academic_cycle=cycle).count() == 2


def test_create_section_rejects_closed_cycle():
    """RF-EST-011: structure is immutable once the cycle is closed."""
    offering = GradeOfferingFactory()
    close_cycle(cycle=offering.academic_cycle)
    offering.refresh_from_db()

    with pytest.raises(DomainError, match="closed"):
        create_section(offering=offering, name="A", capacity=30)


def test_create_section_rejects_negative_capacity():
    offering = GradeOfferingFactory()

    with pytest.raises(DomainError, match="capacity"):
        create_section(offering=offering, name="A", capacity=-1)


def test_create_section_accepts_zero_capacity_as_uncapped():
    offering = GradeOfferingFactory()

    section = create_section(offering=offering, name="A", capacity=0)

    assert section.capacity == 0


def test_create_section_rejects_blank_name():
    offering = GradeOfferingFactory()

    with pytest.raises(DomainError, match="name"):
        create_section(offering=offering, name="   ", capacity=30)


# --------------------------------------------------------------------------- #
# update_section / deactivate_section
# --------------------------------------------------------------------------- #


def test_update_section_can_raise_capacity():
    section = SectionFactory(capacity=30)

    updated = update_section(section=section, capacity=40)

    assert updated.capacity == 40


def test_update_section_rejects_capacity_below_current_occupancy():
    from apps.enrolments.services import create_enrolment

    section = SectionFactory(capacity=3)
    for _ in range(2):
        create_enrolment(
            student=StudentFactory(),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
        )

    with pytest.raises(DomainError, match="occupancy"):
        update_section(section=section, capacity=1)


def test_update_section_allows_capacity_equal_to_occupancy():
    from apps.enrolments.services import create_enrolment

    section = SectionFactory(capacity=5)
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    updated = update_section(section=section, capacity=1)

    assert updated.capacity == 1


def test_update_section_rejects_closed_cycle():
    section = SectionFactory()
    close_cycle(cycle=section.academic_cycle)

    with pytest.raises(DomainError, match="closed"):
        update_section(section=section, capacity=40)


def test_update_section_rejects_duplicate_name_in_offering():
    offering = GradeOfferingFactory()
    create_section(offering=offering, name="A", capacity=30)
    second = create_section(offering=offering, name="B", capacity=30)

    with pytest.raises(DomainError, match="already"):
        update_section(section=second, name="A")


def test_deactivate_section_rejects_when_it_still_has_active_enrolments():
    from apps.enrolments.services import create_enrolment

    section = SectionFactory(capacity=10)
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    with pytest.raises(DomainError, match="enrolment"):
        deactivate_section(section=section)


def test_deactivate_section_preserves_the_record():
    section = SectionFactory()

    deactivate_section(section=section)

    section.refresh_from_db()
    assert section.is_active is False
    assert Section.objects.filter(pk=section.pk).exists()


# --------------------------------------------------------------------------- #
# occupancy reporting (RF-EST-008)
# --------------------------------------------------------------------------- #


def test_uncapped_section_reports_no_seat_limit():
    section = SectionFactory(capacity=0)

    assert section.available_seats is None


def test_level_shortcut_walks_grade_and_level():
    level = LevelFactory(name="Primaria")
    grade = GradeFactory(level=level)
    section = SectionFactory(grade=grade)

    assert section.level == level
    assert section.offering.level == level
