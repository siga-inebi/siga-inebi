from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, serializers
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.people.api.serializers import PersonSerializer, validate_institutional_person
from apps.students import queries, services
from apps.students.api.serializers import StudentGuardianRelationSerializer
from apps.students.models import Student


class GuardianLinkSerializer(serializers.Serializer):
    guardian_id = serializers.IntegerField(min_value=1, required=False)
    person = PersonSerializer(required=False)
    relationship_label = serializers.CharField(max_length=100)

    def validate(self, attrs):
        if set(self.initial_data) - {"guardian_id", "person", "relationship_label"}:
            raise serializers.ValidationError("La solicitud contiene campos no admitidos.")
        if ("guardian_id" in attrs) == ("person" in attrs):
            raise serializers.ValidationError("Seleccione un encargado o complete uno nuevo.")
        if "person" in attrs:
            validate_institutional_person(attrs["person"])
        return attrs


@extend_schema_view(post=extend_schema(responses={201: StudentGuardianRelationSerializer}))
class StudentRecordGuardianLinkView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GuardianLinkSerializer

    def post(self, request, public_id):
        # Authorize the target before validating personal data or creating anything.
        student = queries.student_record_for_action(actor=request.user, public_id=public_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        relation = services.link_guardian_from_record(
            student=student, actor=request.user, **serializer.validated_data
        )
        return Response(StudentGuardianRelationSerializer(relation).data, status=201)


class StudentStatusQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Student.StudentStatus.choices, required=False)


class StudentStatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Student.StudentStatus.choices)
    expected_status = serializers.ChoiceField(choices=Student.StudentStatus.choices)

    def validate(self, attrs):
        if set(self.initial_data) - {"status", "expected_status"}:
            raise serializers.ValidationError("Solo se admite el cambio de estado confirmado.")
        return attrs


class StatusOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class LastStatusChangeSerializer(serializers.Serializer):
    previous_status = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    actor_label = serializers.CharField()
    changed_at = serializers.DateTimeField()


class StudentStatusContextSerializer(serializers.Serializer):
    status = serializers.CharField()
    can_change = serializers.BooleanField()
    options = StatusOptionSerializer(many=True)
    has_active_enrolment = serializers.BooleanField()
    warnings = serializers.ListField(child=serializers.CharField())
    last_change = LastStatusChangeSerializer(allow_null=True)


@extend_schema_view(
    get=extend_schema(parameters=[StudentStatusQuerySerializer]),
    post=extend_schema(
        request=StudentStatusChangeSerializer, responses={200: StudentStatusContextSerializer}
    ),
)
class StudentRecordStatusView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentStatusContextSerializer

    def get(self, request, public_id):
        params = StudentStatusQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        student = queries.student_record_for_action(
            actor=request.user, public_id=public_id, permission="student_view_basic"
        )
        context = queries.student_status_context(
            student=student, actor=request.user, selected_status=params.validated_data.get("status")
        )
        return Response(self.get_serializer(context).data)

    def post(self, request, public_id):
        student = queries.student_record_for_action(actor=request.user, public_id=public_id)
        serializer = StudentStatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.change_student_record_status(
            student=student, actor=request.user, **serializer.validated_data
        )
        return Response(self.get_serializer(result).data)
