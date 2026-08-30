"""
RNF-REN-003 — deferred execution for work that must not run inside a request.

A synchronous request has one budget: the web server's timeout. Work whose
size is decided by data rather than by the request (a batch, a fan-out over
every day of a cycle) has no bound at all, so sooner or later it crosses that
budget and the operator sees a gateway error on a change the database already
committed. Such work is written here instead: the request records *what* has
to happen and returns, and the worker of RNF-REN-004 decides *when*.

The three moving parts are deliberately separate:

``register`` / ``task``
    A name-to-handler table. Handlers are looked up by name at execution
    time, never stored in the row, so the code that runs a job is always the
    code currently deployed.

``enqueue``
    Called from a domain service, inside that service's transaction.

``claim_next_job`` / ``run_job``
    The draining half. ``claim_next_job`` is safe to call from several
    processes at once even though RNF-REN-004 only allows one: correctness
    should not depend on an operational setting that an administrator can
    change.
"""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.common.models import DEFAULT_MAX_ATTEMPTS, Job

logger = logging.getLogger(__name__)

# A failed job is retried a little later rather than immediately: nearly every
# failure a job hits here is a transient one (the database was restarting, a
# file was still being written), and retrying in the same second only spends
# the attempt budget without giving the cause time to clear.
RETRY_BACKOFF = timedelta(minutes=1)

_REGISTRY = {}


class TaskNotRegistered(LookupError):
    """Raised when a job names a handler that no longer exists."""


def register(name, handler):
    """
    Bind ``name`` to ``handler``.

    Re-registering the same name with a *different* function is refused. The
    name is what gets written into rows that outlive the process, so two
    handlers answering to one name means a queued job would run whichever
    module happened to be imported last.
    """
    existing = _REGISTRY.get(name)
    if existing is not None and existing is not handler:
        raise RuntimeError(f"Task '{name}' is already registered to {existing!r}.")
    _REGISTRY[name] = handler
    return handler


def task(name):
    """Decorator form of :func:`register`."""

    def decorator(handler):
        register(name, handler)
        handler.task_name = name
        return handler

    return decorator


def handler_for(name):
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise TaskNotRegistered(name) from exc


def registered_tasks():
    """The registered task names, for the worker's startup log."""
    return sorted(_REGISTRY)


def enqueue(*, task, payload=None, available_at=None, max_attempts=None):
    """
    Record ``task`` to be run later and return the ``Job`` row.

    Call this from inside the domain transaction it belongs to. That is the
    whole point of a table-backed queue: the job appears if and only if the
    change that needs it commits. Using ``transaction.on_commit`` here would
    give up exactly that guarantee, because a crash between commit and
    callback would drop the job silently.

    The task name is resolved now, not at execution time, so a typo fails in
    the request that made it instead of hours later in the worker log.
    """
    handler_for(task)
    return Job.objects.create(
        task=task,
        payload=payload or {},
        available_at=available_at or timezone.now(),
        max_attempts=max_attempts or DEFAULT_MAX_ATTEMPTS,
    )


def claim_next_job(*, now=None):
    """
    Take the oldest due job and mark it running, or return ``None``.

    ``FOR UPDATE SKIP LOCKED`` is what makes the claim atomic: the row is
    locked and marked in one transaction, and any concurrent claimer steps
    over the locked row instead of blocking behind it. Without ``SKIP
    LOCKED`` a second worker would queue up on the same row and then find it
    already running — the lock would serialise workers rather than distribute
    jobs.
    """
    now = now or timezone.now()
    with transaction.atomic():
        job = (
            Job.objects.select_for_update(skip_locked=True)
            .filter(status=Job.Status.QUEUED, available_at__lte=now)
            .order_by("available_at", "pk")
            .first()
        )
        if job is None:
            return None
        job.status = Job.Status.RUNNING
        job.attempts += 1
        job.started_at = now
        job.finished_at = None
        job.save(update_fields=["status", "attempts", "started_at", "finished_at", "updated_at"])
        return job


def run_job(job, *, now=None):
    """
    Execute a claimed job and record its outcome. Returns the updated job.

    Every exception is caught on purpose. A worker that dies on a bad job
    stops draining the queue for everything else, so a failure is data (a
    status and a message on the row) rather than a crash. The one thing that
    is *not* forgiven indefinitely is repetition: once ``attempts`` reaches
    ``max_attempts`` the job stays failed and waits for a person.
    """
    now = now or timezone.now()
    try:
        handler = handler_for(job.task)
        handler(**job.payload)
    except Exception as exc:
        return _record_failure(job, exc, now=now)

    job.status = Job.Status.SUCCEEDED
    job.finished_at = now
    job.last_error = ""
    job.save(update_fields=["status", "finished_at", "last_error", "updated_at"])
    return job


def _record_failure(job, exc, *, now):
    exhausted = job.attempts >= job.max_attempts
    job.last_error = f"{type(exc).__name__}: {exc}"[:2000]
    if exhausted:
        job.status = Job.Status.FAILED
        job.finished_at = now
        logger.error("Job %s (%s) failed permanently: %s", job.pk, job.task, job.last_error)
    else:
        # Back to the queue, invisible until the backoff elapses. `attempts`
        # was already incremented by the claim, so the budget is spent even if
        # the worker is killed mid-job and the row is re-claimed later.
        job.status = Job.Status.QUEUED
        job.available_at = now + RETRY_BACKOFF
        job.finished_at = None
        logger.warning(
            "Job %s (%s) failed on attempt %s/%s: %s",
            job.pk,
            job.task,
            job.attempts,
            job.max_attempts,
            job.last_error,
        )
    job.save(
        update_fields=["status", "available_at", "finished_at", "last_error", "updated_at"],
    )
    return job
