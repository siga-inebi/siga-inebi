"""
RF-JOR-001 — parametros de jornada configurables, en aislamiento.
"""

from datetime import time, timedelta

import pytest

from apps.attendance import services
from apps.attendance.models import JornadaParameters
from apps.common.models import DomainError
from tests.factories.academic import AcademicCycleFactory, CampusFactory, ShiftFactory
from tests.factories.attendance import JornadaParametersFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_two_jornadas_with_different_schedules_evaluate_independently():
    campus = CampusFactory()
    cycle = AcademicCycleFactory(institution=campus.institution)
    morning = ShiftFactory(campus=campus)
    afternoon = ShiftFactory(campus=campus)

    services.set_jornada_parameters(
        shift=morning,
        academic_cycle=cycle,
        entry_limit_time=time(7, 0),
        tolerance_minutes=10,
        closing_time=time(13, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )
    services.set_jornada_parameters(
        shift=afternoon,
        academic_cycle=cycle,
        entry_limit_time=time(13, 30),
        tolerance_minutes=10,
        closing_time=time(18, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )

    morning_params = services.get_effective_parameters(
        shift=morning, academic_cycle=cycle, on_date=cycle.starts_on
    )
    afternoon_params = services.get_effective_parameters(
        shift=afternoon, academic_cycle=cycle, on_date=cycle.starts_on
    )

    assert morning_params.entry_limit_time == time(7, 0)
    assert afternoon_params.entry_limit_time == time(13, 30)


def test_set_jornada_parameters_never_mutates_prior_versions():
    parameters = JornadaParametersFactory(entry_limit_time=time(7, 0))

    services.set_jornada_parameters(
        shift=parameters.shift,
        academic_cycle=parameters.academic_cycle,
        entry_limit_time=time(7, 15),
        tolerance_minutes=parameters.tolerance_minutes,
        closing_time=parameters.closing_time,
        duplicate_suppression_minutes=parameters.duplicate_suppression_minutes,
        school_days=parameters.school_days,
        effective_from=parameters.effective_from + timedelta(days=30),
    )

    parameters.refresh_from_db()
    assert parameters.entry_limit_time == time(7, 0)
    assert JornadaParameters.objects.filter(shift=parameters.shift).count() == 2


def test_get_effective_parameters_picks_the_latest_version_on_or_before_the_date():
    parameters = JornadaParametersFactory(entry_limit_time=time(7, 0))
    later = services.set_jornada_parameters(
        shift=parameters.shift,
        academic_cycle=parameters.academic_cycle,
        entry_limit_time=time(7, 15),
        tolerance_minutes=parameters.tolerance_minutes,
        closing_time=parameters.closing_time,
        duplicate_suppression_minutes=parameters.duplicate_suppression_minutes,
        school_days=parameters.school_days,
        effective_from=parameters.effective_from + timedelta(days=30),
    )

    before = services.get_effective_parameters(
        shift=parameters.shift,
        academic_cycle=parameters.academic_cycle,
        on_date=parameters.effective_from + timedelta(days=1),
    )
    after = services.get_effective_parameters(
        shift=parameters.shift,
        academic_cycle=parameters.academic_cycle,
        on_date=later.effective_from,
    )

    assert before == parameters
    assert after == later


def test_get_effective_parameters_raises_when_none_configured():
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.institution)

    with pytest.raises(DomainError):
        services.get_effective_parameters(
            shift=shift, academic_cycle=cycle, on_date=cycle.starts_on
        )


def test_set_jornada_parameters_rejects_mismatched_institution():
    shift = ShiftFactory()
    other_cycle = AcademicCycleFactory()

    with pytest.raises(DomainError):
        services.set_jornada_parameters(
            shift=shift,
            academic_cycle=other_cycle,
            entry_limit_time=time(7, 0),
            tolerance_minutes=10,
            closing_time=time(13, 0),
            duplicate_suppression_minutes=5,
            school_days=[1, 2, 3, 4, 5],
            effective_from=other_cycle.starts_on,
        )


def test_resolve_academic_cycle_for_finds_the_cycle_covering_the_date():
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.institution)

    resolved = services.resolve_academic_cycle_for(shift=shift, event_date=cycle.starts_on)

    assert resolved == cycle
