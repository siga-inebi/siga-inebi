from datetime import time, timedelta

import factory
from django.utils import timezone

from apps.attendance.models import (
    AttendanceAlert,
    AttendanceEvent,
    AttendancePermit,
    CaptureBatch,
    ControlPoint,
    JornadaParameters,
    Justification,
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
    # Looked up on every call (not bound at import) so ``event_date`` and
    # ``captured_at`` follow the same clock under ``operating_window_clock``.
    captured_at = factory.LazyFunction(lambda: timezone.now())


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


class JustificationFactory(factory.django.DjangoModelFactory):
    """A stored justification, without the submission-window rules (RF-JUS-003)."""

    class Meta:
        model = Justification

    student = factory.SubFactory(StudentFactory)
    absence_date = factory.LazyFunction(lambda: timezone.localdate() - timedelta(days=1))
    reason = "Cita medica"
    submitted_by = factory.SubFactory(UserFactory)


class AttendancePermitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AttendancePermit

    student = factory.SubFactory(StudentFactory)
    permit_type = AttendancePermit.PermitType.EARLY_EXIT
    permit_date = factory.LazyFunction(timezone.localdate)
    scheduled_time = time(13, 0)
    reason = "Cita medica"
    submitted_by = factory.SubFactory(UserFactory)
