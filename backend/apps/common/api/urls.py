from django.urls import path

from .views import TaskHealthView, TaskRunListView

urlpatterns = [
    path("task-runs/", TaskRunListView.as_view(), name="platform-task-run-list"),
    path("task-health/", TaskHealthView.as_view(), name="platform-task-health"),
]
