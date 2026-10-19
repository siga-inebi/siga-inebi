from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.common.exceptions import AuthorizationError
from apps.enrolments import queries
from apps.enrolments.authorization import require_section_scope
from apps.enrolments.bulk_initial import MAX_BATCH_SIZE, bulk_matriculate_students


class BulkMatriculationCreateSerializer(serializers.Serializer):
    section_id = serializers.UUIDField()
    effective_on = serializers.DateField()
    student_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        max_length=MAX_BATCH_SIZE,
    )
    preview = serializers.BooleanField(default=True)

    def validate_student_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Un estudiante no puede repetirse en el lote.")
        return value


class CandidateQuerySerializer(serializers.Serializer):
    section_id = serializers.UUIDField()
    search = serializers.CharField(required=False, allow_blank=True, max_length=100)


class CandidateSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    full_name = serializers.SerializerMethodField()
    student_code = serializers.CharField()

    def get_full_name(self, obj) -> str:
        return f"{obj.person.first_name} {obj.person.last_name}".strip()


class BulkMatriculationResultSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=["ready", "created", "existing", "error"])
    enrolment_id = serializers.UUIDField(allow_null=True)
    error = serializers.CharField(allow_null=True)


class BulkMatriculationResponseSerializer(serializers.Serializer):
    preview = serializers.BooleanField()
    total = serializers.IntegerField()
    succeeded = serializers.IntegerField()
    failed = serializers.IntegerField()
    results = BulkMatriculationResultSerializer(many=True)


class BulkMatriculationCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BulkMatriculationCreateSerializer

    @extend_schema(
        summary="Revisar o ejecutar altas iniciales por lote",
        responses={200: BulkMatriculationResponseSerializer},
        tags=["enrolments"],
    )
    def post(self, request):
        if not request.user.has_atomic_permission("enrollment_create"):
            raise AuthorizationError("El actor no tiene el permiso requerido.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        result = bulk_matriculate_students(
            actor=request.user,
            section=queries.section_or_404(payload["section_id"]),
            student_ids=payload["student_ids"],
            effective_on=payload["effective_on"],
            preview=payload["preview"],
        )
        return Response(result)


class InitialMatriculationCandidatesView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CandidateQuerySerializer

    @extend_schema(
        summary="Buscar candidatos para alta inicial",
        parameters=[CandidateQuerySerializer],
        responses={200: CandidateSerializer(many=True)},
        tags=["enrolments"],
    )
    def get(self, request):
        if not request.user.has_atomic_permission("enrollment_create"):
            raise AuthorizationError("El actor no tiene el permiso requerido.")
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        section = queries.section_or_404(payload["section_id"])
        require_section_scope(actor=request.user, codenames="enrollment_create", sections=[section])
        page = self.paginate_queryset(
            queries.initial_matriculation_candidates(
                actor=request.user,
                section=section,
                search=payload.get("search", ""),
            )
        )
        return self.get_paginated_response(CandidateSerializer(page, many=True).data)
