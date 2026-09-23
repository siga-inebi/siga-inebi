"""Read-side queries for the shared platform layer."""

from apps.common.exceptions import ResourceNotFoundError
from apps.common.models import TaskRun


def task_runs(*, name=None, status=None):
    """Recent executions first, optionally narrowed to one task or outcome."""
    runs = TaskRun.objects.all()
    if name:
        runs = runs.filter(name=name)
    if status:
        runs = runs.filter(status=status)
    return runs


def task_run_or_404(public_id):
    try:
        return TaskRun.objects.get(public_id=public_id)
    except TaskRun.DoesNotExist as exc:
        raise ResourceNotFoundError("TaskRun not found.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("TaskRun not found.") from exc
