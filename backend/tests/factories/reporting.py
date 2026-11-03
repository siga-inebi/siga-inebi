import factory
from django.utils import timezone

from apps.reporting.models import AbsenceThresholdParameters, Alert
from tests.factories.academic import AcademicCycleFactory, ShiftFactory
from tests.factories.students import StudentFactory


class AbsenceThresholdParametersFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AbsenceThresholdParameters

    shift = factory.SubFactory(ShiftFactory)
    academic_cycle = factory.LazyAttribute(
        lambda obj: AcademicCycleFactory(institution=obj.shift.institution)
    )
    max_absences = 3
    lookback_days = 10
    effective_from = factory.LazyAttribute(lambda obj: obj.academic_cycle.starts_on)


class ReportingAlertFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Alert

    alert_type = Alert.AlertType.ABSENCE_NOT_REGISTERED
    student = factory.SubFactory(StudentFactory)
    shift = factory.SubFactory(ShiftFactory)
    section = None
    event_date = factory.LazyFunction(timezone.localdate)
    target_roles = factory.LazyFunction(list)
    context = factory.LazyFunction(dict)
