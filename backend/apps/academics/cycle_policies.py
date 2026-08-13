from apps.academics.models import AcademicCycle
from apps.common.models import DomainError


def require_cycle_academic_writes(*, cycle, actor=None, operation):
    """Deny academic mutations once a cycle becomes historical (RF-CIC-002)."""
    if cycle.status != AcademicCycle.CycleStatus.CLOSED:
        return

    raise DomainError("Closed academic cycles do not accept academic changes.")
