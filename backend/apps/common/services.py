"""Domain services for the shared platform layer (RNF-OPE-001)."""

from django.db.models import Count, Max, Q

from apps.common.exceptions import AuthorizationError
from apps.common.models import TaskRun

PLATFORM_MONITOR_PERMISSION = "platform_monitor"


def ensure_platform_monitor_permission(*, actor):
    """Only the system administrator reads the operational picture."""
    if actor is None or not actor.has_atomic_permission(PLATFORM_MONITOR_PERMISSION):
        raise AuthorizationError("Actor lacks the required permission.")


def task_health_summary(*, actor):
    """
    One row per known task: when it last ran and how it went (RNF-OPE-001).

    The list of tasks is derived from the runs themselves rather than from a
    registry of what SHOULD run. A registry would have to be kept in sync by
    hand and would go stale; what an administrator needs first is the shape of
    what actually happened, and a task that has never run at all is visible by
    its absence from a list that is short enough to read.
    """
    ensure_platform_monitor_permission(actor=actor)

    rows = (
        TaskRun.objects.values("name")
        .annotate(
            total_runs=Count("id"),
            failed_runs=Count("id", filter=Q(status=TaskRun.Status.FAILED)),
            running_runs=Count("id", filter=Q(status=TaskRun.Status.RUNNING)),
            last_started_at=Max("started_at"),
            last_finished_at=Max("finished_at"),
        )
        .order_by("name")
    )

    summary = []
    for row in rows:
        last_run = TaskRun.objects.filter(name=row["name"]).order_by("-started_at", "-id").first()
        summary.append(
            {
                **row,
                "last_status": last_run.status if last_run else "",
                "last_duration_ms": last_run.duration_ms if last_run else None,
                "last_error_message": last_run.error_message if last_run else "",
            }
        )
    return summary
