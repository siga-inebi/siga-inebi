from rest_framework import generics, permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.common.models import DomainError
from apps.students import services
from apps.students.api import queries
from apps.students.api.serializers import (
    EmergencyContactCreateSerializer,
    EmergencyContactSerializer,
    EmergencyContactUpdateSerializer,
    GuardianRefSerializer,
    GuardianSerializer,
    StudentGuardianRelationCreateSerializer,
    StudentGuardianRelationSerializer,
    StudentGuardianRelationUpdateSerializer,
    StudentSerializer,
)
from apps.students.models import Guardian, Student
from apps.students.services import deactivate_guardian, deactivate_student


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


# --------------------------------------------------------------------------- #
# local scaffolding
#
# Mirrors apps.academics.api.views (list-create nested under the parent,
# detail flat by the resource's own public_id, same as Shift/Grade there).
# Duplicated on purpose instead of imported: keeps student-records
# independent of institutional-structure (AGENTS.md #9).
# --------------------------------------------------------------------------- #


class StudentRecordView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def validated(self, serializer_class, request):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class StudentRecordListCreateView(StudentRecordView):
    list_serializer = None
    create_serializer = None

    def get_serializer_class(self):
        if self.request.method == "POST":
            return self.create_serializer
        return self.list_serializer

    def get(self, request, **kwargs):
        page = self.paginate_queryset(self.list_queryset(request, **kwargs))
        return self.get_paginated_response(self.list_serializer(page, many=True).data)

    def post(self, request, **kwargs):
        payload = self.validated(self.create_serializer, request)
        created = self.create(request, payload, **kwargs)
        return Response(self.list_serializer(created).data, status=status.HTTP_201_CREATED)


class StudentRecordDetailView(StudentRecordView):
    detail_serializer = None
    update_serializer = None

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return self.update_serializer
        return self.detail_serializer

    def represent(self, instance):
        return Response(self.detail_serializer(instance).data)


class RetrieveMixin:
    def get(self, request, **kwargs):
        return self.represent(self.get_object(**kwargs))


class UpdateMixin:
    def patch(self, request, **kwargs):
        payload = self.validated(self.update_serializer, request)
        self.update(request, self.get_object(**kwargs), payload)
        return self.represent(self.get_object(**kwargs))


class DeactivateMixin:
    def delete(self, request, **kwargs):
        self.deactivate(request, self.get_object(**kwargs))
        return Response(status=status.HTTP_204_NO_CONTENT)


class StudentEmergencyContactListCreateView(StudentRecordListCreateView):
    list_serializer = EmergencyContactSerializer
    create_serializer = EmergencyContactCreateSerializer

    def list_queryset(self, request, public_id):
        return queries.emergency_contacts(queries.student_or_404(public_id), request)

    def create(self, request, payload, public_id):
        student = queries.student_or_404(public_id)
        return services.create_emergency_contact(student=student, actor=request.user, **payload)


class EmergencyContactDetailView(
    RetrieveMixin, UpdateMixin, DeactivateMixin, StudentRecordDetailView
):
    detail_serializer = EmergencyContactSerializer
    update_serializer = EmergencyContactUpdateSerializer

    def get_object(self, public_id):
        return queries.emergency_contact_or_404(public_id)

    def update(self, request, emergency_contact, payload):
        services.update_emergency_contact(
            emergency_contact=emergency_contact, actor=request.user, **payload
        )

    def deactivate(self, request, emergency_contact):
        services.deactivate_emergency_contact(
            emergency_contact=emergency_contact, actor=request.user
        )


# --------------------------------------------------------------------------- #
# guardians — read-only options for a "link existing guardian" selector
# --------------------------------------------------------------------------- #


class GuardianOptionListView(generics.ListAPIView):
    """Active guardians, unpaginated reference list for the relation form."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GuardianRefSerializer
    pagination_class = None

    def get_queryset(self):
        return queries.guardian_options(self.request)


# --------------------------------------------------------------------------- #
# student <-> guardian relations — nested under a student
# --------------------------------------------------------------------------- #


def _resolve_guardian(public_id):
    """
    Resolve a reference that arrived in the request body. A bad reference in a
    payload is a bad request, not a missing endpoint, so it lands as a 400
    (mirrors apps.academics.api.views._resolve). Resolved without an
    is_active filter on purpose: the service is the one that must report an
    inactive guardian, not a generic "not found".
    """
    try:
        return Guardian.objects.select_related("person").get(public_id=public_id)
    except Guardian.DoesNotExist as exc:
        raise DomainError("Guardian not found.") from exc


class StudentGuardianRelationListCreateView(StudentRecordListCreateView):
    list_serializer = StudentGuardianRelationSerializer
    create_serializer = StudentGuardianRelationCreateSerializer

    def list_queryset(self, request, public_id):
        return queries.student_guardian_relations(queries.student_or_404(public_id), request)

    def create(self, request, payload, public_id):
        student = queries.student_or_404(public_id)
        guardian = _resolve_guardian(payload.pop("guardian_id"))
        return services.create_student_guardian_relation(
            student=student, guardian=guardian, actor=request.user, **payload
        )


class StudentGuardianRelationDetailView(
    RetrieveMixin, UpdateMixin, DeactivateMixin, StudentRecordDetailView
):
    """``deactivate`` here means "end the relation" (sets ``ends_at``)."""

    detail_serializer = StudentGuardianRelationSerializer
    update_serializer = StudentGuardianRelationUpdateSerializer

    def get_object(self, public_id):
        return queries.student_guardian_relation_or_404(public_id)

    def update(self, request, relation, payload):
        services.update_student_guardian_relation(relation=relation, actor=request.user, **payload)

    def deactivate(self, request, relation):
        services.end_student_guardian_relation(relation=relation, actor=request.user)
