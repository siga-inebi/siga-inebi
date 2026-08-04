import pytest

from apps.academics.models import AcademicCycle
from apps.academics.services import close_cycle, open_cycle
from apps.common.models import DomainError
from tests.factories.academic import AcademicCycleFactory

# ---------------------------------------------------------------------------
# open_cycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.django_db
def test_open_cycle_transitions_draft_to_active():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)

    open_cycle(cycle=cycle)
    cycle.refresh_from_db()

    assert cycle.status == AcademicCycle.CycleStatus.ACTIVE


@pytest.mark.unit
@pytest.mark.django_db
def test_open_cycle_rejects_already_active():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)

    with pytest.raises(DomainError, match="already active"):
        open_cycle(cycle=cycle)


@pytest.mark.unit
@pytest.mark.django_db
def test_open_cycle_rejects_closed_cycle():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)

    with pytest.raises(DomainError, match="closed"):
        open_cycle(cycle=cycle)


@pytest.mark.unit
@pytest.mark.django_db
def test_open_cycle_rejects_when_another_active_exists_in_same_institution():
    existing = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    draft = AcademicCycleFactory(
        institution=existing.institution,
        status=AcademicCycle.CycleStatus.DRAFT,
    )

    with pytest.raises(DomainError, match="active cycle"):
        open_cycle(cycle=draft)


@pytest.mark.unit
@pytest.mark.django_db
def test_open_cycle_allows_draft_when_no_other_active_in_institution():
    draft = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)

    open_cycle(cycle=draft)
    draft.refresh_from_db()

    assert draft.status == AcademicCycle.CycleStatus.ACTIVE


# ---------------------------------------------------------------------------
# close_cycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.django_db
def test_close_cycle_transitions_active_to_closed():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)

    close_cycle(cycle=cycle)
    cycle.refresh_from_db()

    assert cycle.status == AcademicCycle.CycleStatus.CLOSED


@pytest.mark.unit
@pytest.mark.django_db
def test_close_cycle_rejects_draft():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)

    with pytest.raises(DomainError, match="only active"):
        close_cycle(cycle=cycle)


@pytest.mark.unit
@pytest.mark.django_db
def test_close_cycle_rejects_already_closed():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)

    with pytest.raises(DomainError, match="only active"):
        close_cycle(cycle=cycle)


@pytest.mark.unit
@pytest.mark.django_db
def test_closed_cycle_does_not_allow_new_sections():
    """
    RF-EST-011: structure is immutable once cycle is closed.
    This test verifies the invariant lives in the service, not the model.
    """
    from apps.academics.services import create_section
    from tests.factories.academic import GradeOfferingFactory

    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    offering = GradeOfferingFactory(academic_cycle=cycle)

    close_cycle(cycle=cycle)
    offering.refresh_from_db()

    with pytest.raises(DomainError, match="closed"):
        create_section(offering=offering, name="A", capacity=30)
