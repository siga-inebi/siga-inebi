from django.urls import path

from apps.students.api.views import StudentDetailView, StudentListCreateView

urlpatterns = [
    path("", StudentListCreateView.as_view(), name="student-list"),
    path("<int:pk>/", StudentDetailView.as_view(), name="student-detail"),
]
