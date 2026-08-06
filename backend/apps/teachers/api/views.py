from rest_framework import generics

from apps.teachers.api.serializers import TeacherSerializer
from apps.teachers.models import Teacher
from apps.teachers.services import deactivate_teacher


class TeacherListCreateView(generics.ListCreateAPIView):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer


class TeacherDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer

    def perform_destroy(self, instance):
        deactivate_teacher(teacher=instance, actor=self.request.user)
