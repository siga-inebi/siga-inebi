from rest_framework import generics

from apps.students.api.serializers import StudentSerializer
from apps.students.models import Student
from apps.students.services import deactivate_student


class StudentListCreateView(generics.ListCreateAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer


class StudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def perform_destroy(self, instance):
        deactivate_student(student=instance, actor=self.request.user)
