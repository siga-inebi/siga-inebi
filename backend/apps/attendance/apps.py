from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.attendance"

    def ready(self):
        from apps.attendance import receivers  # noqa: F401
