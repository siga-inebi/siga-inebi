"""
Domain rules of the cycle-scoped structure: cycles, grade offerings and sections.

What hangs from a cycle is rebuilt for each one (RF-EST-013) and stops being
mutable once the cycle closes (RF-EST-011), so most tests here are about those
two boundaries rather than about field validation.
"""

import datetime

import pytest

from apps.academics.models import AcademicCycle, GradeOffering, Section
from apps.academics.services import (
    change_cycle_status,
    create_academic_cycle,
    create_section,
    deactivate_section,
    offer_grade,
    update_academic_cycle,
    update_section,
    withdraw_grade_offering,
)
from apps.common.models import DomainError
from apps.enrolments.services import create_enrolment
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    GradeFactory,
    GradeOfferingFactory,
    InstitutionFactory,
    SectionFactory,
    ShiftFactory,
)
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

TODAY = datetime.date(2026, 1, 15)
YEAR_END = datetime.date(2026, 11, 30)


def _draft_cycle(institution=None):
    return AcademicCycleFactory(
        institution=institution or InstitutionFactory(),
        status=AcademicCycle.CycleStatus.DRAFT,
    )


def _grade_and_shift(institution):
    """A grade and a shift that both belong to the given institution."""
    return (
        GradeFactory(institution=institution),
        ShiftFactory(campus=CampusFactory(institution=institution)),
    )


def _enrol(section, count=1):
    """Occupancy is what blocks withdrawals and capacity cuts, so tests need it."""
    for _ in range(count):
        create_enrolment(
            student=StudentFactory(),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
        )


# --------------------------------------------------------------------------- #
# create_academic_cycle
# --------------------------------------------------------------------------- #


def test_create_cycle_is_born_in_draft():
    institution = InstitutionFactory()

    cycle = create_academic_cycle(
        institution=institution, name="  Ciclo 2026 ", starts_on=TODAY, ends_on=YEAR_END
    )

    assert cycle.name == "Ciclo 2026"
    assert cycle.status == AcademicCycle.CycleStatus.DRAFT


def test_create_cycle_rejects_duplicate_name_in_institution():
    institution = InstitutionFactory()
    create_academic_cycle(
        institution=institution, name="Ciclo 2026", starts_on=TODAY, ends_on=YEAR_END
    )

    with pytest.raises(DomainError, match="already exists"):
        create_academic_cycle(
            institution=institution, name="Ciclo 2026", starts_on=TODAY, ends_on=YEAR_END
        )


def test_same_cycle_name_is_free_in_another_institution():
    create_academic_cycle(
        institution=InstitutionFactory(), name="Ciclo 2026", starts_on=TODAY, ends_on=YEAR_END
    )

    other = create_academic_cycle(
        institution=InstitutionFactory(), name="Ciclo 2026", starts_on=TODAY, ends_on=YEAR_END
    )

    assert other.pk is not None


@pytest.mark.parametrize("ends_on", [TODAY, TODAY - datetime.timedelta(days=1)])
def test_create_cycle_rejects_end_date_not_after_start(ends_on):
    with pytest.raises(DomainError, match="later than"):
        create_academic_cycle(
            institution=InstitutionFactory(), name="Ciclo", starts_on=TODAY, ends_on=ends_on
        )


# --------------------------------------------------------------------------- #
# update_academic_cycle
# --------------------------------------------------------------------------- #


def test_update_cycle_renames_and_moves_dates():
    cycle = _draft_cycle()

    update_academic_cycle(cycle=cycle, name="Ciclo 2027", ends_on=YEAR_END)
    cycle.refresh_from_db()

    assert cycle.name == "Ciclo 2027"
    assert cycle.ends_on == YEAR_END


def test_update_cycle_validates_dates_against_the_stored_ones():
    """Sending only one date still has to keep the pair coherent."""
    cycle = AcademicCycleFactory(starts_on=TODAY, ends_on=YEAR_END)

    with pytest.raises(DomainError, match="later than"):
        update_academic_cycle(cycle=cycle, ends_on=TODAY - datetime.timedelta(days=10))


def test_closed_cycle_cannot_be_edited():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)

    with pytest.raises(DomainError, match="closed"):
        update_academic_cycle(cycle=cycle, name="Otro nombre")


# --------------------------------------------------------------------------- #
# change_cycle_status
# --------------------------------------------------------------------------- #


def test_cycle_cannot_be_activated_while_it_has_no_offering():
    cycle = _draft_cycle()

    with pytest.raises(DomainError, match="no grade offering"):
        change_cycle_status(cycle=cycle, status=AcademicCycle.CycleStatus.ACTIVE)


def test_cycle_is_activated_once_it_offers_a_grade():
    cycle = _draft_cycle()
    GradeOfferingFactory(academic_cycle=cycle)

    change_cycle_status(cycle=cycle, status=AcademicCycle.CycleStatus.ACTIVE)

    assert cycle.status == AcademicCycle.CycleStatus.ACTIVE


def test_cycle_status_only_moves_forward():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)

    with pytest.raises(DomainError, match="cannot move"):
        change_cycle_status(cycle=cycle, status=AcademicCycle.CycleStatus.DRAFT)


def test_closed_cycle_never_reopens():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)

    with pytest.raises(DomainError, match="cannot move"):
        change_cycle_status(cycle=cycle, status=AcademicCycle.CycleStatus.ACTIVE)


def test_active_cycle_can_be_closed():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)

    change_cycle_status(cycle=cycle, status=AcademicCycle.CycleStatus.CLOSED)

    assert cycle.is_closed


def test_change_cycle_status_rejects_an_unknown_status():
    with pytest.raises(DomainError, match="Unknown cycle status"):
        change_cycle_status(cycle=_draft_cycle(), status="paused")


# --------------------------------------------------------------------------- #
# offer_grade
# --------------------------------------------------------------------------- #


def test_offer_grade_links_cycle_shift_and_grade():
    cycle = _draft_cycle()
    grade, shift = _grade_and_shift(cycle.institution)

    offering = offer_grade(cycle=cycle, grade=grade, shift=shift)

    assert offering.campus == shift.campus
    assert offering.institution == cycle.institution


def test_offer_grade_rejects_the_same_trio_twice():
    cycle = _draft_cycle()
    grade, shift = _grade_and_shift(cycle.institution)
    offer_grade(cycle=cycle, grade=grade, shift=shift)

    with pytest.raises(DomainError, match="already offered"):
        offer_grade(cycle=cycle, grade=grade, shift=shift)


def test_offer_grade_rejects_an_inactive_grade():
    cycle = _draft_cycle()
    grade, shift = _grade_and_shift(cycle.institution)
    grade.is_active = False
    grade.save(update_fields=["is_active"])

    with pytest.raises(DomainError, match="inactive"):
        offer_grade(cycle=cycle, grade=grade, shift=shift)


def test_offer_grade_rejects_a_grade_from_another_institution():
    cycle = _draft_cycle()
    _, shift = _grade_and_shift(cycle.institution)
    foreign_grade = GradeFactory(institution=InstitutionFactory())

    with pytest.raises(DomainError, match="same institution"):
        offer_grade(cycle=cycle, grade=foreign_grade, shift=shift)


def test_offer_grade_rejects_a_shift_from_another_institution():
    cycle = _draft_cycle()
    grade, _ = _grade_and_shift(cycle.institution)
    foreign_shift = ShiftFactory(campus=CampusFactory(institution=InstitutionFactory()))

    with pytest.raises(DomainError, match="same institution"):
        offer_grade(cycle=cycle, grade=grade, shift=foreign_shift)


def test_closed_cycle_accepts_no_new_offering():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)
    grade, shift = _grade_and_shift(cycle.institution)

    with pytest.raises(DomainError, match="closed"):
        offer_grade(cycle=cycle, grade=grade, shift=shift)


# --------------------------------------------------------------------------- #
# withdraw_grade_offering
# --------------------------------------------------------------------------- #


def test_withdrawing_an_offering_deactivates_its_sections():
    section = SectionFactory()
    offering = section.offering

    withdraw_grade_offering(offering=offering)
    section.refresh_from_db()

    assert GradeOffering.objects.get(pk=offering.pk).is_active is False
    assert section.is_active is False


def test_withdrawing_an_offering_is_idempotent():
    offering = GradeOfferingFactory(is_active=False)

    assert withdraw_grade_offering(offering=offering).is_active is False


def test_offering_with_active_enrolments_cannot_be_withdrawn():
    section = SectionFactory()
    _enrol(section)

    with pytest.raises(DomainError, match="active enrolments"):
        withdraw_grade_offering(offering=section.offering)


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #


def test_create_section_normalises_the_name():
    offering = GradeOfferingFactory()

    section = create_section(offering=offering, name=" a ", capacity=30)

    assert section.name == "A"
    assert section.capacity == 30


def test_create_section_rejects_a_duplicate_name_in_the_offering():
    offering = GradeOfferingFactory()
    create_section(offering=offering, name="A")

    with pytest.raises(DomainError, match="already exists"):
        create_section(offering=offering, name="a")


def test_same_section_name_is_free_in_another_offering():
    institution = InstitutionFactory()
    cycle = _draft_cycle(institution)
    first = GradeOfferingFactory(academic_cycle=cycle)
    second = GradeOfferingFactory(academic_cycle=cycle)
    create_section(offering=first, name="A")

    assert create_section(offering=second, name="A").pk is not None


def test_create_section_rejects_a_negative_capacity():
    with pytest.raises(DomainError, match="cannot be negative"):
        create_section(offering=GradeOfferingFactory(), name="A", capacity=-1)


def test_capacity_zero_means_no_declared_cap():
    section = create_section(offering=GradeOfferingFactory(), name="A", capacity=0)

    assert section.available_seats is None


def test_capacity_cannot_drop_below_current_occupancy():
    section = SectionFactory(capacity=30)
    _enrol(section, count=2)

    with pytest.raises(DomainError, match="capacity cannot be set below"):
        update_section(section=section, capacity=1)


def test_capacity_can_be_raised_and_reports_available_seats():
    section = SectionFactory(capacity=1)
    _enrol(section)

    update_section(section=section, capacity=10)
    stored = Section.objects.get(pk=section.pk)

    assert stored.capacity == 10
    assert stored.available_seats == 9


def test_section_with_active_enrolments_cannot_be_deactivated():
    section = SectionFactory()
    _enrol(section)

    with pytest.raises(DomainError, match="active enrolments"):
        deactivate_section(section=section)


def test_empty_section_is_deactivated():
    section = SectionFactory()

    deactivate_section(section=section)

    assert section.is_active is False


def test_sections_of_a_closed_cycle_are_frozen():
    section = SectionFactory()
    cycle = section.academic_cycle
    cycle.status = AcademicCycle.CycleStatus.CLOSED
    cycle.save(update_fields=["status"])

    with pytest.raises(DomainError, match="closed"):
        update_section(section=section, name="B")
