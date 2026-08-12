from datetime import date

import pytest

from apps.academics.models import AcademicCycle, GradeOffering
from apps.academics.services import activate_academic_cycle, create_academic_cycle
from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from tests.factories.academic import GradeFactory, InstitutionFactory, ShiftFactory
from tests.factories.identity import UserFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_prepared_cycle_accepts_structure_while_active_cycle_remains_current():
    institution = InstitutionFactory()
    actor = UserFactory()
    active = create_academic_cycle(
        institution=institution,
        year=2026,
        name="Ciclo 2026",
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 10, 31),
        actor=actor,
    )
    activate_academic_cycle(cycle=active, actor=actor)
    prepared = create_academic_cycle(
        institution=institution,
        year=2027,
        name="Ciclo 2027",
        starts_on=date(2027, 1, 1),
        ends_on=date(2027, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(level__institution=institution)
    shift = ShiftFactory(campus__institution=institution)

    offering = GradeOffering.objects.create(
        academic_cycle=prepared,
        grade=grade,
        shift=shift,
    )

    assert offering.pk is not None
    assert prepared.status == AcademicCycle.CycleStatus.DRAFT
    with pytest.raises(DomainError, match="must be closed"):
        activate_academic_cycle(cycle=prepared, actor=actor)
    assert AuditEvent.objects.filter(action="academics.cycle.created").count() == 2
