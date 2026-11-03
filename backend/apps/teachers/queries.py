"""Read-side queries for the teachers domain."""

from apps.common.exceptions import DomainError, ResourceNotFoundError
from apps.teachers.authorization import may_deactivate_teacher
from apps.teachers.models import Teacher


def teacher_positions():
    """Published position choices; no duplicate catalogue in the UI."""
    return [{"value": value, "label": label} for value, label in Teacher.Position.choices]


def teacher_action_permissions(*, actor):
    """Resolve module-level access once per response, never once per list row."""
    return {"deactivate": may_deactivate_teacher(actor)}


def teacher_actions(*, teacher, permissions):
    return {"deactivate": bool(teacher.is_active and permissions.get("deactivate", False))}


def teachers(*, include_inactive=True, position=None):
    queryset = Teacher.objects.select_related("person").all()
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    if position is not None:
        queryset = queryset.filter(position=position)
    return queryset


def teacher_or_404(public_id):
    try:
        return teachers().get(public_id=public_id)
    except Teacher.DoesNotExist as exc:
        raise ResourceNotFoundError("No se encontró el docente.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("No se encontró el docente.") from exc


def teacher_for_payload(public_id):
    try:
        return teachers().get(public_id=public_id)
    except (Teacher.DoesNotExist, ValueError, TypeError) as exc:
        raise DomainError("No se encontró el docente.") from exc
