from datetime import time

import factory
from django.utils import timezone

from apps.attendance.models import AttendanceAlert, AttendanceEvent, JornadaParameters
from tests.factories.academic import AcademicCycleFactory, ShiftFactory
from tests.factories.students import StudentFactory


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


class AttendanceEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AttendanceEvent

    student = factory.SubFactory(StudentFactory)
    shift = factory.SubFactory(ShiftFactory)
    event_date = factory.LazyFunction(timezone.localdate)
    movement_type = AttendanceEvent.MovementType.EXIT
    origin = AttendanceEvent.Origin.SCAN
    transmission = AttendanceEvent.Transmission.INDIVIDUAL
    captured_at = factory.LazyFunction(timezone.now)


class AttendanceAlertFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AttendanceAlert

    alert_type = AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE
    student = factory.SubFactory(StudentFactory)
    shift = factory.SubFactory(ShiftFactory)
    section = None
    event_date = factory.LazyFunction(timezone.localdate)
    target_roles = factory.LazyFunction(list)
    context = factory.LazyFunction(dict)
