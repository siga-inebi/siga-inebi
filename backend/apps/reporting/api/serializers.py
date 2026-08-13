from rest_framework import serializers

from apps.reporting.models import AbsenceThresholdParameters, Alert


class AbsenceThresholdParametersSerializer(serializers.ModelSerializer):
    shift_id = serializers.UUIDField(source="shift.public_id", read_only=True)
    academic_cycle_id = serializers.UUIDField(source="academic_cycle.public_id", read_only=True)

    class Meta:
        model = AbsenceThresholdParameters
        fields = [
            "public_id",
            "shift_id",
            "academic_cycle_id",
            "max_absences",
            "lookback_days",
            "effective_from",
            "is_active",
            "created_at",
        ]


class AbsenceThresholdParametersCreateSerializer(serializers.Serializer):
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada (Shift).")
    academic_cycle_id = serializers.UUIDField(help_text="Public ID del ciclo escolar.")
    max_absences = serializers.IntegerField(
        min_value=1, help_text="Cantidad de ausencias que activa la alerta."
    )
    lookback_days = serializers.IntegerField(
        min_value=1, help_text="Ventana de dias lectivos evaluados, terminando en la fecha evaluada."
    )
    effective_from = serializers.DateField(help_text="Fecha desde la que rige este umbral.")


class ReportingAlertSerializer(serializers.ModelSerializer):
    student_id = serializers.UUIDField(source="student.public_id", read_only=True)
    shift_id = serializers.UUIDField(source="shift.public_id", read_only=True)
    section_id = serializers.UUIDField(source="section.public_id", read_only=True, allow_null=True)
    acknowledged_by_username = serializers.CharField(
        source="acknowledged_by.username", read_only=True, allow_null=True, default=None
    )

    class Meta:
        model = Alert
        fields = [
            "public_id",
            "alert_type",
            "student_id",
            "shift_id",
            "section_id",
            "event_date",
            "target_roles",
            "context",
            "is_active",
            "acknowledged_at",
            "acknowledged_by_username",
            "created_at",
        ]


class ReportingAlertQuerySerializer(serializers.Serializer):
    shift_id = serializers.UUIDField(required=False)
    event_date = serializers.DateField(required=False)
    alert_type = serializers.ChoiceField(choices=Alert.AlertType.choices, required=False)
    is_active = serializers.BooleanField(required=False)
    acknowledged = serializers.BooleanField(required=False)


class AlertEvaluationRequestSerializer(serializers.Serializer):
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada (Shift).")
    event_date = serializers.DateField(help_text="Fecha de la jornada a evaluar.")


class DailyAlertEvaluationResultSerializer(serializers.Serializer):
    shift_id = serializers.UUIDField(source="shift.public_id")
    event_date = serializers.DateField()
    synced_alerts = ReportingAlertSerializer(many=True)
    superseded_source_alerts = ReportingAlertSerializer(many=True)
    absence_alerts = ReportingAlertSerializer(many=True)
    frequent_absence_alerts = ReportingAlertSerializer(many=True)
