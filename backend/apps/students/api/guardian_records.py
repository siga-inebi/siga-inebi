from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, permissions, serializers
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response

from apps.students import queries, services
from apps.students.models import Student, StudentGuardianRelation


class GuardianStudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="person.__str__", read_only=True)

    class Meta:
        model = Student
        fields = ["public_id", "student_code", "full_name", "is_active", "status"]


class GuardianStudentRelationSerializer(serializers.ModelSerializer):
    student = GuardianStudentSerializer(read_only=True)

    class Meta:
        model = StudentGuardianRelation
        fields = [
            "id",
            "student",
            "relationship_label",
            "is_primary",
            "starts_at",
            "ends_at",
            "is_active",
        ]


class GuardianStudentActionsSerializer(serializers.Serializer):
    link_student = serializers.BooleanField()


class GuardianStudentsPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = GuardianStudentRelationSerializer(many=True)
    actions = GuardianStudentActionsSerializer()


class GuardianStudentLinkSerializer(serializers.Serializer):
    student_public_id = serializers.UUIDField()
    relationship_label = serializers.CharField(max_length=100)

    def validate(self, attrs):
        if set(self.initial_data) - {"student_public_id", "relationship_label"}:
            raise serializers.ValidationError("La solicitud contiene campos no admitidos.")
        return attrs


class GuardianRecordResponseMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class GuardianStudentsView(GuardianRecordResponseMixin, GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GuardianStudentRelationSerializer

    @extend_schema(
        parameters=[OpenApiParameter("page", int), OpenApiParameter("page_size", int)],
        responses={200: GuardianStudentsPageSerializer},
    )
    def get(self, request, pk):
        guardian = queries.guardian_or_404(pk)
        rows = queries.guardian_record_relations(actor=request.user, guardian=guardian)
        page = self.paginate_queryset(rows)
        response = self.get_paginated_response(self.get_serializer(page, many=True).data)
        response.data["actions"] = queries.guardian_record_actions(
            actor=request.user, guardian=guardian
        )
        return response

    @extend_schema(
        request=GuardianStudentLinkSerializer, responses={201: GuardianStudentRelationSerializer}
    )
    def post(self, request, pk):
        payload = GuardianStudentLinkSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        relation = services.link_student_from_guardian(
            actor=request.user, guardian_id=pk, **payload.validated_data
        )
        return Response(self.get_serializer(relation).data, status=201)


class GuardianStudentCandidatesView(GuardianRecordResponseMixin, ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GuardianStudentSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["student_code", "person__first_name", "person__last_name"]

    def get_queryset(self):
        guardian = queries.guardian_or_404(self.kwargs["pk"])
        rows = queries.guardian_student_candidates(actor=self.request.user, guardian=guardian)
        # Do not download a roster for an empty or one-character picker query.
        return (
            rows if len(self.request.query_params.get("search", "").strip()) >= 2 else rows.none()
        )
