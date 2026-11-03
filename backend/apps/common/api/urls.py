from django.urls import path

from .views import BackupHealthView, TaskHealthView, TaskRunListView

urlpatterns = [
    path("task-runs/", TaskRunListView.as_view(), name="platform-task-run-list"),
    path("task-health/", TaskHealthView.as_view(), name="platform-task-health"),
    path("backup-health/", BackupHealthView.as_view(), name="platform-backup-health"),
]
