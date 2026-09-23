import uuid

from django.db import models

from .exceptions import DomainError

__all__ = ["DomainError", "TaskRun", "TimeStampedModel"]


class TimeStampedModel(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class TaskRun(TimeStampedModel):
    """
    One execution of a background or scheduled task (RNF-OPE-001).

    Logs alone do not answer the question an administrator actually has, which
    is "did last night's job run, and how did it end". Console output is
    ephemeral, lives on whatever host ran the job, and a task that never
    started leaves no line at all. A row does: a task scheduled but missing
    from this table is a task that did not run.

    Rows are append-then-finish: ``start_task_run`` writes one as ``running``
    and the same run is closed exactly once. They are history, so they are
    never deleted and never rewritten after being closed -- the same contract
    as ``apps.audit.models.AuditEvent`` (RN-BIT-001), minus the actor: these
    executions have no human behind them.
    """

    class Status(models.TextChoices):
        RUNNING = "running", "En ejecucion"
        SUCCEEDED = "succeeded", "Finalizada"
        FAILED = "failed", "Fallida"

    name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Identificador estable de la tarea, normalmente el comando que la ejecuta.",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    host = models.CharField(max_length=255, blank=True, default="")
    process_id = models.PositiveIntegerField(null=True, blank=True)
    # Whatever the task wants an administrator to see: counters, totals,
    # identifiers it touched. Free-form on purpose -- every task summarises
    # itself differently and none of them should need a schema change to do it.
    summary = models.JSONField(default=dict, blank=True)
    error_type = models.CharField(max_length=150, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["name", "-started_at"], name="task_run_name_recent_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.status}) {self.started_at:%Y-%m-%d %H:%M}"

    @property
    def is_finished(self):
        return self.status != self.Status.RUNNING

    def delete(self, *args, **kwargs):
        raise RuntimeError("Task runs cannot be deleted.")
