"""
Base for management commands that run unattended (RNF-OPE-001).

Cron is the only scheduler this deployment has, and cron's memory is a mail
spool nobody reads. A command that inherits from ``MonitoredCommand`` leaves a
``TaskRun`` row and a structured log line for every execution without its own
code having to remember to, which is the point: the instrumentation must not be
something each task opts into correctly.
"""

from django.core.management.base import BaseCommand

from apps.common.tasks import task_run


class MonitoredCommand(BaseCommand):
    """
    Wraps ``handle`` in a recorded task run.

    Subclasses implement ``run(*args, **options)`` and receive a ``summary``
    dict in ``options`` to fill with whatever an administrator should see. The
    task name defaults to the command's module name, so it stays stable when
    the class is renamed and matches what an operator typed into cron.
    """

    task_name = None

    def run(self, *args, **options):  # pragma: no cover - interface
        raise NotImplementedError

    def handle(self, *args, **options):
        name = self.task_name or self.__module__.rsplit(".", 1)[-1]
        with task_run(name) as summary:
            options["summary"] = summary
            return self.run(*args, **options)
