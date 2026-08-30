from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.attendance"

    def ready(self):
        # Registers this domain's deferred handlers (RNF-REN-003). Without the
        # import, a job row naming one of them would find no handler and the
        # worker would fail it as unknown.
        from apps.attendance import tasks  # noqa: F401
