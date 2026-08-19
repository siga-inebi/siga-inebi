from rest_framework import serializers

from apps.academics.models import Section
from apps.enrolments.models import Enrolment, EnrolmentDocumentRequirement


class SectionOccupancySerializer(serializers.ModelSerializer):
    """Declared capacity plus real-time occupancy for a section (RF-EST-008)."""

    academic_cycle_id = serializers.UUIDField(
        source="offering.academic_cycle.public_id", read_only=True
    )
    grade_id = serializers.UUIDField(source="offering.grade.public_id", read_only=True)
    occupied_seats = serializers.IntegerField(source="active_enrolment_count", read_only=True)
    available_seats = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Section
        fields = [
            "public_id",
            "name",
            "capacity",
            "occupied_seats",
            "available_seats",
            "academic_cycle_id",
            "grade_id",
        ]


class SectionOccupancyQuerySerializer(serializers.Serializer):
    academic_cycle_id = serializers.UUIDField(required=False, help_text="Filtra por ciclo.")
    grade_id = serializers.UUIDField(required=False, help_text="Filtra por grado.")
    section_id = serializers.UUIDField(required=False, help_text="Consulta una sola sección.")
    include_inactive = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Incluye secciones desactivadas. Por defecto solo las activas.",
    )


class EnrolmentDocumentRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnrolmentDocumentRequirement
        fields = [
            "public_id",
            "code",
            "name",
            "is_required",
            "status",
            "created_at",
            "updated_at",
        ]


class EnrolmentDocumentRequirementCreateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50, help_text="Codigo del documento requerido.")
    name = serializers.CharField(max_length=150, help_text="Nombre del documento requerido.")
    is_required = serializers.BooleanField(
        required=False,
        help_text="Solo se actualiza si viene en el payload. Al crear, por defecto es true.",
    )
    status = serializers.ChoiceField(
        choices=EnrolmentDocumentRequirement.DeliveryStatus.choices,
        required=False,
        help_text=(
            "Solo se actualiza si viene en el payload. Al crear, por defecto es 'pending'. "
            "Omitirlo en una actualizacion conserva el estado de entrega registrado."
        ),
    )


class EnrolmentSerializer(serializers.ModelSerializer):
    student_id = serializers.UUIDField(source="student.public_id", read_only=True)
    academic_cycle_id = serializers.UUIDField(source="academic_cycle.public_id", read_only=True)
    grade_id = serializers.UUIDField(source="grade.public_id", read_only=True)
    section_id = serializers.UUIDField(source="section.public_id", read_only=True)

    class Meta:
        model = Enrolment
        fields = [
            "public_id",
            "student_id",
            "academic_cycle_id",
            "grade_id",
            "section_id",
            "effective_on",
            "ends_on",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]


class EnrolmentCreateSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID del estudiante.")
    academic_cycle_id = serializers.UUIDField(help_text="Public ID del ciclo escolar.")
    grade_id = serializers.UUIDField(help_text="Public ID del grado.")
    section_id = serializers.UUIDField(help_text="Public ID de la sección.")
    effective_on = serializers.DateField(help_text="Fecha de inicio de la vigencia.")
    ends_on = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Fecha final opcional de la vigencia.",
    )


class ActiveEnrolmentQuerySerializer(serializers.Serializer):
    student_id = serializers.UUIDField(required=False, help_text="Filtra por estudiante.")


class EnrolmentHistoryQuerySerializer(serializers.Serializer):
    student_id = serializers.UUIDField(required=True, help_text="Public ID del estudiante.")


class MatriculationSerializer(EnrolmentSerializer):
    shift_id = serializers.UUIDField(source="section.shift.public_id", read_only=True)

    class Meta:
        model = Enrolment
        fields = EnrolmentSerializer.Meta.fields + ["shift_id"]


class MatriculationCreateSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID del estudiante pre-enrolled.")
    academic_cycle_id = serializers.UUIDField(help_text="Public ID del ciclo escolar.")
    grade_id = serializers.UUIDField(help_text="Public ID del grado.")
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada.")
    section_id = serializers.UUIDField(help_text="Public ID de la sección asignada.")
    effective_on = serializers.DateField(help_text="Fecha de inicio de la matrícula.")


class ReenrolmentCreateSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID del estudiante activo.")
    academic_cycle_id = serializers.UUIDField(help_text="Public ID del nuevo ciclo escolar.")
    grade_id = serializers.UUIDField(help_text="Public ID del grado destino.")
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada destino.")
    section_id = serializers.UUIDField(help_text="Public ID de la sección asignada.")
    effective_on = serializers.DateField(help_text="Fecha de inicio de la reinscripción.")
