from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers
from rest_framework.generics import GenericAPIView

from apps.enrolments import queries
from apps.enrolments.models import Enrolment


class StudentRecordEnrolmentSerializer(serializers.ModelSerializer):
    is_current = serializers.BooleanField(read_only=True)
    cycle_name = serializers.CharField(source="academic_cycle.name")
    grade_name = serializers.CharField(source="grade.name")
    section_name = serializers.CharField(source="section.name")
    shift_name = serializers.CharField(source="section.shift.name")

    class Meta:
        model = Enrolment
        fields = [
            "public_id",
            "is_current",
            "cycle_name",
            "grade_name",
            "section_name",
            "shift_name",
            "status",
            "effective_on",
            "ends_on",
        ]


class StudentRecordEnrolmentsView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentRecordEnrolmentSerializer

    @extend_schema(
        responses={200: StudentRecordEnrolmentSerializer(many=True)}, tags=["enrolments"]
    )
    def get(self, request, student_id):
        page = self.paginate_queryset(
            queries.student_record_enrolments(actor=request.user, public_id=student_id)
        )
        return self.get_paginated_response(self.get_serializer(page, many=True).data)
