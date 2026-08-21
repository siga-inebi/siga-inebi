from apps.common.exceptions import DomainError


def require_cycle_academic_writes(*, cycle, operation):
    """Deny academic mutations once a cycle becomes historical (RF-CIC-002)."""
    if not cycle.is_closed:
        return

    raise DomainError(f"Un ciclo escolar cerrado no admite cambios academicos: {operation}.")


def require_cycle_planning_writes(*, cycle, operation):
    """
    Deny structural mutations once a cycle leaves planning (RF-EST-011).

    Stricter than ``require_cycle_academic_writes``: operational writes (a
    teaching assignment, an enrolment) stay allowed for the whole time a cycle
    is ``ACTIVE`` (RF-CIC-002); the structure itself (grade offerings,
    sections) is only editable while the cycle is still ``DRAFT``. Callers
    that need both rules call ``require_cycle_academic_writes`` first, so a
    closed cycle keeps reporting the closed-cycle message.
    """
    if cycle.is_planning:
        return

    raise DomainError(
        f"La estructura del ciclo escolar solo cambia mientras esta en preparacion: {operation}."
    )
