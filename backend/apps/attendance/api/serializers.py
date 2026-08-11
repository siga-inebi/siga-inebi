from rest_framework import serializers

from apps.attendance.models import JornadaParameters


class JornadaParametersSerializer(serializers.ModelSerializer):
    shift_id = serializers.UUIDField(source="shift.public_id", read_only=True)
    academic_cycle_id = serializers.UUIDField(source="academic_cycle.public_id", read_only=True)

    class Meta:
        model = JornadaParameters
        fields = [
            "public_id",
            "shift_id",
            "academic_cycle_id",
            "entry_limit_time",
            "tolerance_minutes",
            "closing_time",
            "duplicate_suppression_minutes",
            "school_days",
            "effective_from",
            "is_active",
            "created_at",
        ]


class JornadaParametersCreateSerializer(serializers.Serializer):
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada (Shift).")
    academic_cycle_id = serializers.UUIDField(help_text="Public ID del ciclo escolar.")
    entry_limit_time = serializers.TimeField(help_text="Hora limite de ingreso.")
    tolerance_minutes = serializers.IntegerField(
        min_value=0, help_text="Minutos de tolerancia de llegada tardia."
    )
    closing_time = serializers.TimeField(help_text="Hora de cierre de la jornada.")
    duplicate_suppression_minutes = serializers.IntegerField(
        min_value=0, help_text="Ventana de supresion de duplicados, en minutos."
    )
    school_days = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=7),
        help_text="Dias lectivos de la semana (1=lunes .. 7=domingo).",
    )
    effective_from = serializers.DateField(
        help_text="Fecha desde la que rigen estos parametros."
    )
