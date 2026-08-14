from apps.common.models import DomainError


def require_cycle_academic_writes(*, cycle, operation):
    """Deny academic mutations once a cycle becomes historical (RF-CIC-002)."""
    if not cycle.is_closed:
        return

    raise DomainError(f"Closed academic cycles do not accept academic changes: {operation}.")
