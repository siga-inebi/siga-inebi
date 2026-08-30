import uuid

from django.db import models
from django.utils import timezone

from .exceptions import DomainError

__all__ = ["DEFAULT_MAX_ATTEMPTS", "DomainError", "Job", "TimeStampedModel"]

# Three tries is the budget for a transient cause to clear. Beyond that the
# failure is structural and more attempts only delay a person looking at it.
DEFAULT_MAX_ATTEMPTS = 3


class TimeStampedModel(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Job(TimeStampedModel):
    """
    RNF-REN-003: a unit of work moved out of the synchronous request cycle.

    The queue is a table, not a broker. Two reasons, in this order. The first
    is correctness: a job row is written inside the same transaction as the
    domain change that asks for it, so a rolled-back request cannot leave an
    orphan job behind, and a committed one cannot lose its follow-up work.
    An external broker gets that guarantee only with an outbox — which is this
    table anyway. The second is operational: the establishment runs a single
    institution on a single host, and a broker would be one more process to
    keep alive during the school day for no capacity we need.

    Payload is JSON on purpose. Storing a pickled callable would tie every
    queued row to the exact code that enqueued it, so a deploy in between
    would resurrect old behaviour; a task name plus plain data lets the
    handler that runs be the one currently deployed.
    """

    class Status(models.TextChoices):
        QUEUED = "queued", "En cola"
        RUNNING = "running", "En ejecucion"
        SUCCEEDED = "succeeded", "Completado"
        FAILED = "failed", "Fallido"

    task = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    # Both the retry backoff and the RNF-REN-004 window need a job to be
    # invisible until a moment in the future, and one column serves both.
    available_at = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=DEFAULT_MAX_ATTEMPTS)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        indexes = [
            # The claim query is the only hot read: it filters on status plus
            # available_at and orders by the same column the filter uses, so
            # one composite index answers it without a sort.
            models.Index(
                fields=["status", "available_at"],
                name="common_job_claim_idx",
            )
        ]

    def __str__(self):
        return f"{self.task} ({self.status})"
