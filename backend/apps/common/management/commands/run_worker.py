"""
RNF-REN-004 — the process that drains the deferred-job queue.
"""

import logging
import signal
import time as time_module

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.common import jobs
from apps.common.worker import (
    InvalidWindow,
    parse_window_time,
    single_worker_lock,
    window_is_open,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ejecuta el proceso trabajador que drena la cola de trabajos diferidos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help=(
                "Realiza una sola pasada y termina, en lugar de quedarse en el bucle. "
                "La ventana horaria se sigue respetando."
            ),
        )

    def handle(self, *args, **options):
        try:
            start = parse_window_time(settings.WORKER_WINDOW_START, setting="WORKER_WINDOW_START")
            end = parse_window_time(settings.WORKER_WINDOW_END, setting="WORKER_WINDOW_END")
        except InvalidWindow as exc:
            raise CommandError(str(exc)) from exc

        # The flag is read between jobs, never in the middle of one. A worker
        # that dropped a running job on SIGTERM would leave the row marked
        # running with nothing running it, and the job would only come back
        # after someone noticed.
        self._stopping = False
        for received in (signal.SIGINT, signal.SIGTERM):
            signal.signal(received, self._request_stop)

        with single_worker_lock(settings.WORKER_CONCURRENCY_LOCK_ID) as acquired:
            if not acquired:
                # Not an error: the process manager restarting the worker
                # while the old one still holds the lock is ordinary, and the
                # right answer is to step aside quietly.
                self.stdout.write(
                    "Ya hay un proceso trabajador en ejecucion; este termina sin tomar trabajos."
                )
                return

            registered = ", ".join(jobs.registered_tasks()) or "ninguna"
            self.stdout.write(
                f"Trabajador iniciado. Ventana local {start:%H:%M}-{end:%H:%M}, "
                f"concurrencia 1, tareas registradas: {registered}."
            )
            self._drain(start=start, end=end, once=options["once"])
            self.stdout.write("Trabajador detenido.")

    def _request_stop(self, _signum, _frame):
        self._stopping = True

    def _drain(self, *, start, end, once):
        poll_seconds = settings.WORKER_POLL_SECONDS
        while not self._stopping:
            if not window_is_open(timezone.localtime().time(), start=start, end=end):
                # Deliberately before any query: outside the window the worker
                # must not even hold a database connection busy, because the
                # scanning point is what that connection is for.
                if once:
                    self.stdout.write("Fuera de la ventana horaria; no se toma ningun trabajo.")
                    return
                self._sleep(poll_seconds)
                continue

            job = jobs.claim_next_job()
            if job is None:
                if once:
                    return
                self._sleep(poll_seconds)
                continue

            logger.info("Ejecutando el trabajo %s (%s).", job.pk, job.task)
            jobs.run_job(job)
            if once:
                return

    def _sleep(self, seconds):
        """Sleep in one-second slices so a stop signal is answered promptly."""
        for _ in range(max(int(seconds), 1)):
            if self._stopping:
                return
            time_module.sleep(1)
