from datetime import time

import factory
from django.utils import timezone

from apps.attendance.models import (
    AttendanceAlert,
    AttendanceEvent,
    CaptureBatch,
    ControlPoint,
    JornadaParameters,
    ManualRegistrationReason,
    StudentCredential,
)
from tests.factories.academic import AcademicCycleFactory, CampusFactory, ShiftFactory
from tests.factories.identity import UserFactory
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


class ControlPointFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ControlPoint

    campus = factory.SubFactory(CampusFactory)
    name = factory.Sequence(lambda n: f"Punto de control {n}")
    code = factory.Sequence(lambda n: f"CP{n}")


class ManualRegistrationReasonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ManualRegistrationReason

    name = factory.Sequence(lambda n: f"Motivo {n}")
    code = factory.Sequence(lambda n: f"MOT{n}")


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


class StudentCredentialFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentCredential

    student = factory.SubFactory(StudentFactory)
    opaque_identifier = factory.Sequence(lambda n: f"opaque-token-{n}")
    status = StudentCredential.Status.ACTIVE
    issued_at = factory.LazyFunction(timezone.now)


class CaptureBatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CaptureBatch

    operator = factory.SubFactory(UserFactory)
    status = CaptureBatch.Status.OPEN
