"""Read-side queries for the teachers domain."""

from apps.common.exceptions import DomainError, ResourceNotFoundError
from apps.teachers.models import Teacher


def teachers():
    return Teacher.objects.select_related("person").all()


def teacher_or_404(public_id):
    try:
        return teachers().get(public_id=public_id)
    except Teacher.DoesNotExist as exc:
        raise ResourceNotFoundError("No se encontro el docente.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("Teacher not found.") from exc


def teacher_for_payload(public_id):
    try:
        return teachers().get(public_id=public_id)
    except (Teacher.DoesNotExist, ValueError, TypeError) as exc:
        raise DomainError("No se encontro el docente.") from exc
