from django.core.exceptions import PermissionDenied
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.identity.scopes import authorized_student_queryset
from apps.students import services
from apps.students.api import queries
from apps.students.api.serializers import (
    EmergencyContactCreateSerializer,
    EmergencyContactSerializer,
    EmergencyContactUpdateSerializer,
    GuardianSerializer,
    StudentGuardianRelationEndSerializer,
    StudentGuardianRelationSerializer,
    StudentSerializer,
)
from apps.students.models import Guardian, Student, StudentGuardianRelation
from apps.students.services import (
    change_primary_student_guardian_relation,
    deactivate_guardian,
    deactivate_student,
    end_student_guardian_relation,
)


class StudentListCreateView(generics.ListCreateAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def get_queryset(self):
        return authorized_student_queryset(
            user=self.request.user,
            codename="student_view_basic",
            queryset=super().get_queryset(),
        )

    def perform_create(self, serializer):
        user = self.request.user
        if not user.has_scoped_permission("student_edit_basic", scope={"module_key": "students"}):
            raise PermissionDenied("Actor lacks the required permission or scope.")
        serializer.save()


class StudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def get_queryset(self):
        codename = "student_view_basic" if self.request.method == "GET" else "student_edit_basic"
        return authorized_student_queryset(
            user=self.request.user,
            codename=codename,
            queryset=super().get_queryset(),
        )

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

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                student__in=authorized_student_queryset(
                    user=self.request.user,
                    codename="student_view_basic",
                )
            )
        )

    def perform_create(self, serializer):
        student = serializer.validated_data["student"]
        if not self.request.user.has_scoped_permission(
            "student_edit_basic", scope={"student": student}
        ):
            raise PermissionDenied("Actor lacks the required permission or student scope.")
        serializer.save()


class StudentGuardianRelationDetailView(generics.RetrieveAPIView):
    queryset = StudentGuardianRelation.objects.all()
    serializer_class = StudentGuardianRelationSerializer

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                student__in=authorized_student_queryset(
                    user=self.request.user,
                    codename="student_view_basic",
                )
            )
        )


class StudentGuardianRelationPrimaryView(GenericAPIView):
    queryset = StudentGuardianRelation.objects.all()
    serializer_class = StudentGuardianRelationSerializer

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                student__in=authorized_student_queryset(
                    user=self.request.user,
                    codename="student_edit_basic",
                )
            )
        )

    def post(self, request, pk):
        relation = self.get_object()
        relation = change_primary_student_guardian_relation(relation=relation, actor=request.user)
        return Response(self.get_serializer(relation).data)


class StudentGuardianRelationEndView(GenericAPIView):
    queryset = StudentGuardianRelation.objects.all()
    serializer_class = StudentGuardianRelationEndSerializer

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                student__in=authorized_student_queryset(
                    user=self.request.user,
                    codename="student_edit_basic",
                )
            )
        )

    def post(self, request, pk):
        relation = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        relation = end_student_guardian_relation(
            relation=relation,
            actor=request.user,
            replacement_relation=serializer.validated_data.get("replacement_relation"),
        )
        return Response(StudentGuardianRelationSerializer(relation).data)


# --------------------------------------------------------------------------- #
# emergency contacts — nested under a student
#
# Small, local scaffolding mirroring apps.academics.api.views (list-create
# nested under the parent, detail flat by the resource's own public_id, same
# as Shift/Grade there). Duplicated on purpose instead of imported: keeps
# student-records independent of institutional-structure (AGENTS.md #9).
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


@extend_schema_view(
    get=extend_schema(
        summary="Listar contactos de emergencia de un estudiante",
        tags=["students: emergency contacts"],
        # `StudentRecordListCreateView.get` pagina dentro del handler, algo que
        # drf-spectacular no puede inferir desde `get_serializer_class`: sin esta
        # anotacion documenta un objeto suelto en vez del sobre paginado.
        responses={200: EmergencyContactSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Registrar contacto de emergencia",
        tags=["students: emergency contacts"],
        request=EmergencyContactCreateSerializer,
        responses={201: EmergencyContactSerializer},
    ),
)
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
