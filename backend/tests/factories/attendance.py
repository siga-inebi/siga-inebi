from datetime import time

import factory

from apps.attendance.models import JornadaParameters
from tests.factories.academic import AcademicCycleFactory, ShiftFactory


class JornadaParametersFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = JornadaParameters

    shift = factory.SubFactory(ShiftFactory)
    academic_cycle = factory.LazyAttribute(
        lambda obj: AcademicCycleFactory(institution=obj.shift.institution)
    )
    entry_limit_time = time(7, 30)
    tolerance_minutes = 10
    closing_time = time(16, 0)
    duplicate_suppression_minutes = 5
    school_days = [1, 2, 3, 4, 5]
    effective_from = factory.LazyAttribute(lambda obj: obj.academic_cycle.starts_on)
