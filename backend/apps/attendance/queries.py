"""Read-side queries and reference resolution for attendance."""

from apps.academics.models import AcademicCycle, Grade, Section, Shift
from apps.attendance.models import (
    AttendanceAlert,
    AttendanceEvent,
    ControlPoint,
    JornadaParameters,
    ManualRegistrationReason,
)
from apps.common.exceptions import DomainError, ResourceNotFoundError
from apps.students.models import Student


def jornada_parameters():
    return JornadaParameters.objects.select_related("shift", "academic_cycle").all()


def attendance_events(*, students):
    return AttendanceEvent.objects.filter(student__in=students).select_related("student", "shift")


def attendance_alerts(*, students):
    return AttendanceAlert.objects.filter(student__in=students).select_related(
        "student", "shift", "section"
    )


def control_points():
    return ControlPoint.objects.select_related("campus").all()


def manual_registration_reasons():
    return ManualRegistrationReason.objects.all()


def _payload_get(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except (queryset.model.DoesNotExist, ValueError, TypeError) as exc:
        raise DomainError(f"No se encontro {label}.") from exc


def student_for_payload(public_id):
    return _payload_get(Student.objects.all(), public_id, "el estudiante")


def shift_for_payload(public_id):
    return _payload_get(Shift.objects.all(), public_id, "la jornada")


def grade_for_payload(public_id):
    return _payload_get(Grade.objects.all(), public_id, "el grado")


def section_for_payload(public_id):
    return _payload_get(Section.objects.all(), public_id, "la seccion")


def academic_cycle_for_payload(public_id):
    return _payload_get(AcademicCycle.objects.all(), public_id, "el ciclo escolar")


def control_point_for_payload(public_id):
    return _payload_get(ControlPoint.objects.all(), public_id, "el punto de control")


def manual_reason_for_payload(public_id):
    return _payload_get(ManualRegistrationReason.objects.all(), public_id, "el motivo")


def student_by_code(student_code):
    return Student.objects.filter(student_code=student_code, is_active=True).first()


def scan_transmission(*, batch_id, item_count):
    return (
        AttendanceEvent.Transmission.BATCH
        if batch_id or item_count > 1
        else AttendanceEvent.Transmission.INDIVIDUAL
    )


def origin_permissions():
    return {
        AttendanceEvent.Origin.SCAN: "attendance_scan",
        AttendanceEvent.Origin.MANUAL: "attendance_record_manual",
        AttendanceEvent.Origin.DECLARED: "attendance_declared_close",
    }


def movement_type_permissions():
    return {
        AttendanceEvent.MovementType.ENTRY: "attendance_record_entry",
        AttendanceEvent.MovementType.EXIT: "attendance_record_exit",
    }


def no_event_error():
    return ResourceNotFoundError(
        "No se encontro movimiento de asistencia para los criterios indicados."
    )
