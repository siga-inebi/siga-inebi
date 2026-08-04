from rest_framework import generics

from apps.students.api.serializers import (
    EmergencyContactSerializer,
    GuardianSerializer,
    StudentGuardianRelationSerializer,
    StudentSerializer,
)
from apps.students.models import EmergencyContact, Guardian, Student, StudentGuardianRelation
from apps.students.services import (
    deactivate_emergency_contact,
    deactivate_guardian,
    deactivate_student,
    end_student_guardian_relation,
)


class StudentListCreateView(generics.ListCreateAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer


class StudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def perform_destroy(self, instance):
        deactivate_student(student=instance, actor=self.request.user)


class GuardianListCreateView(generics.ListCreateAPIView):
    queryset = Guardian.objects.all()
    serializer_class = GuardianSerializer


class GuardianDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Guardian.objects.all()
    serializer_class = GuardianSerializer

    def perform_destroy(self, instance):
        deactivate_guardian(guardian=instance, actor=self.request.user)


class StudentGuardianRelationListCreateView(generics.ListCreateAPIView):
    queryset = StudentGuardianRelation.objects.all()
    serializer_class = StudentGuardianRelationSerializer


class StudentGuardianRelationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StudentGuardianRelation.objects.all()
    serializer_class = StudentGuardianRelationSerializer

    def perform_destroy(self, instance):
        end_student_guardian_relation(relation=instance, actor=self.request.user)


class EmergencyContactListCreateView(generics.ListCreateAPIView):
    queryset = EmergencyContact.objects.all()
    serializer_class = EmergencyContactSerializer


class EmergencyContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EmergencyContact.objects.all()
    serializer_class = EmergencyContactSerializer

    def perform_destroy(self, instance):
        deactivate_emergency_contact(emergency_contact=instance, actor=self.request.user)
