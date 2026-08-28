"""
Deferred handlers for the attendance domain (RNF-REN-003).

A handler is the thin edge between a JSON payload and a domain service: it
rehydrates the arguments and calls the service, and holds no rules of its own
(AGENTS.md #8). Import happens in ``AttendanceConfig.ready`` so that a name
written into a job row always has a handler by the time a worker reads it.
"""

from datetime import date

from apps.academics.models import AcademicCycle, Shift
from apps.attendance import services
from apps.common.jobs import task
from apps.identity.models import UserAccount


@task(services.RECALCULATE_PARAMETERS_CHANGE_TASK)
def recalculate_parameters_change(*, shift_id, academic_cycle_id, effective_from, actor_id=None):
    """
    Reconcile the days a new ``JornadaParameters`` version can have staled
    (RF-JOR-006), off the request that created that version.

    The rows are read now rather than trusted from the payload: a job can sit
    in the queue until the worker's window opens, and what matters is the
    state at execution time.
    """
    services.recalculate_days_for_parameters_change(
        shift=Shift.objects.get(pk=shift_id),
        academic_cycle=AcademicCycle.objects.get(pk=academic_cycle_id),
        effective_from=date.fromisoformat(effective_from),
        actor=UserAccount.objects.filter(pk=actor_id).first() if actor_id else None,
    )
