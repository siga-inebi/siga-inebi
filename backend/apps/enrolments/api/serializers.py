from rest_framework import serializers

from apps.academics.models import Section
from apps.enrolments.models import (
    Enrolment,
    EnrolmentDocumentRequirement,
    StudentMovement,
    StudentMovementAnnulment,
)


class StudentMovementAnnulmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentMovementAnnulment
        fields = ["public_id", "reason", "created_at"]


class StudentMovementAnnulmentCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        help_text="Motivo obligatorio de la anulacion.",
    )


class StudentMovementSerializer(serializers.ModelSerializer):
    annulment = StudentMovementAnnulmentSerializer(read_only=True, allow_null=True)
    student_id = serializers.UUIDField(source="student.public_id", read_only=True)
    source_enrolment_id = serializers.UUIDField(
        source="source_enrolment.public_id", read_only=True, allow_null=True
    )
    target_enrolment_id = serializers.UUIDField(
        source="target_enrolment.public_id", read_only=True, allow_null=True
    )

    class Meta:
        model = StudentMovement
        fields = [
            "public_id",
            "student_id",
            "movement_type",
            "effective_on",
            "reason",
            "source_enrolment_id",
            "target_enrolment_id",
            "annulment",
            "created_at",
        ]


class StudentMovementQuerySerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID del estudiante.")


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


class BulkReenrolmentItemSerializer(serializers.Serializer):
    source_enrolment_id = serializers.UUIDField(
        help_text="Matricula seleccionada del ciclo anterior."
    )
    target_section_id = serializers.UUIDField(help_text="Seccion elegida del ciclo siguiente.")


class BulkReenrolmentCreateSerializer(serializers.Serializer):
    preview = serializers.BooleanField(default=True)
    effective_on = serializers.DateField(help_text="Fecha de inicio de las nuevas matriculas.")
    items = BulkReenrolmentItemSerializer(many=True, allow_empty=False)

    def validate_items(self, value):
        source_ids = [item["source_enrolment_id"] for item in value]
        if len(source_ids) != len(set(source_ids)):
            raise serializers.ValidationError(
                "Una matricula de origen no puede repetirse en el lote."
            )
        return value


class SectionChangeCreateSerializer(serializers.Serializer):
    new_section_id = serializers.UUIDField(help_text="Public ID de la seccion destino.")
    effective_on = serializers.DateField(help_text="Fecha efectiva del cambio.")


class StudentWithdrawalCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        help_text="Causa formal del retiro.",
    )
    effective_on = serializers.DateField(help_text="Fecha efectiva del retiro.")


class StudentTransferInCreateSerializer(MatriculationCreateSerializer):
    pass


class StudentTransferOutCreateSerializer(serializers.Serializer):
    effective_on = serializers.DateField(help_text="Fecha efectiva del traslado de salida.")
    reason = serializers.CharField(required=False, allow_blank=True, default="")
