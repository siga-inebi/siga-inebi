"""Read-side reference resolution for reporting alerts."""

from apps.academics.models import AcademicCycle, Shift
from apps.common.exceptions import DomainError
from apps.reporting.models import AbsenceThresholdParameters, Alert


def absence_threshold_parameters():
    return AbsenceThresholdParameters.objects.select_related("shift", "academic_cycle").all()


def _payload_get(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except (queryset.model.DoesNotExist, ValueError, TypeError) as exc:
        raise DomainError(f"No se encontro {label}.") from exc


def shift_for_payload(public_id):
    return _payload_get(Shift.objects.all(), public_id, "Shift")


def academic_cycle_for_payload(public_id):
    return _payload_get(AcademicCycle.objects.all(), public_id, "Academic cycle")


def alert_for_payload(public_id):
    return _payload_get(Alert.objects.select_related("student"), public_id, "Alert")
