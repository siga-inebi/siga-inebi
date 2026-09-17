from rest_framework import serializers

from apps.audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(
        source="actor.username", read_only=True, allow_null=True, default=None
    )

    class Meta:
        model = AuditEvent
        fields = [
            "public_id",
            "actor_id",
            "actor_label",
            "actor_username",
            "action",
            "resource",
            "resource_identifier",
            "ip_address",
            "context",
            "created_at",
        ]


class DataRetentionDeclarationSerializer(serializers.Serializer):
    category = serializers.CharField(
        help_text="Categoria de datos a la que aplica la retencion, p. ej. student.health_notes."
    )
    period_days = serializers.IntegerField(
        min_value=1, help_text="Plazo de retencion declarado, en dias."
    )
    legal_basis = serializers.CharField(
        help_text="Justificacion legal o institucional del plazo declarado."
    )
    applies_to_minors = serializers.BooleanField(default=False)


class ResultTraceUnitGradeSerializer(serializers.Serializer):
    unit_number = serializers.IntegerField()
    unit_name = serializers.CharField()
    value = serializers.IntegerField()


class ResultTraceCorrectionSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=["live", "post_freeze"])
    unit_number = serializers.IntegerField(allow_null=True)
    previous_value = serializers.IntegerField(allow_null=True)
    new_value = serializers.IntegerField(allow_null=True)
    reason = serializers.CharField(allow_null=True, allow_blank=True)
    corrected_by = serializers.CharField(allow_null=True, allow_blank=True)
    corrected_at = serializers.DateTimeField()


class ResultTraceSerializer(serializers.Serializer):
    """RF-RES-009: unit grades, corrections (with reason and author) and the
    recovery grade behind one subarea's final grade."""

    enrolment_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()
    unit_grades = ResultTraceUnitGradeSerializer(many=True)
    recovery_grade = serializers.IntegerField(allow_null=True)
    corrections = ResultTraceCorrectionSerializer(many=True)


class AuditEventQuerySerializer(serializers.Serializer):
    actor_id = serializers.IntegerField(required=False, help_text="Usuario autor del asiento.")
    resource = serializers.CharField(required=False, help_text="Capacidad o recurso afectado.")
    resource_identifier = serializers.CharField(
        required=False,
        help_text=(
            "Identificador del recurso afectado, p. ej. el pk del estudiante para "
            "resource=Document (RF-EMI-007)."
        ),
    )
    action = serializers.CharField(
        required=False, help_text="Tipo de accion exacto, p. ej. documents.template.created."
    )
    date_from = serializers.DateField(
        required=False, help_text="Fecha inicial del rango (inclusive)."
    )
    date_to = serializers.DateField(required=False, help_text="Fecha final del rango (inclusive).")
