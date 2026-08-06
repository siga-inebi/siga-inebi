from django.urls import path

from apps.teachers.api.views import TeacherDetailView, TeacherListCreateView

urlpatterns = [
    path("", TeacherListCreateView.as_view(), name="teacher-list"),
    path("<int:pk>/", TeacherDetailView.as_view(), name="teacher-detail"),
]
