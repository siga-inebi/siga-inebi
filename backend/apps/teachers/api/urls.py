from django.urls import path

from apps.teachers.api.views import (
    TeacherDetailView,
    TeacherListCreateView,
    TeacherNextCodeView,
    TeacherPositionListView,
)

urlpatterns = [
    path("", TeacherListCreateView.as_view(), name="teacher-list"),
    path("next-code/", TeacherNextCodeView.as_view(), name="teacher-next-code"),
    path("positions/", TeacherPositionListView.as_view(), name="teacher-position-list"),
    path("<int:pk>/", TeacherDetailView.as_view(), name="teacher-detail"),
]
