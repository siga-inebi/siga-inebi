from rest_framework import serializers

from apps.attendance.models import AttendanceAlert, AttendanceEvent, DayStatus, JornadaParameters


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
    effective_from = serializers.DateField(help_text="Fecha desde la que rigen estos parametros.")


class AttendanceEventSerializer(serializers.ModelSerializer):
    student_id = serializers.UUIDField(source="student.public_id", read_only=True)
    shift_id = serializers.UUIDField(source="shift.public_id", read_only=True)

    class Meta:
        model = AttendanceEvent
        fields = [
            "public_id",
            "student_id",
            "shift_id",
            "event_date",
            "movement_type",
            "origin",
            "transmission",
            "captured_at",
            "is_active",
            "created_at",
        ]


class AttendanceEventCreateSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID del estudiante.")
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada (Shift).")
    event_date = serializers.DateField(help_text="Fecha de la jornada.")
    movement_type = serializers.ChoiceField(choices=AttendanceEvent.MovementType.choices)
    origin = serializers.ChoiceField(choices=AttendanceEvent.Origin.choices)
    transmission = serializers.ChoiceField(
        choices=AttendanceEvent.Transmission.choices,
        required=False,
        default=AttendanceEvent.Transmission.INDIVIDUAL,
    )
    captured_at = serializers.DateTimeField(help_text="Hora de captura del evento.")


class DayStatusQuerySerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    shift_id = serializers.UUIDField()
    event_date = serializers.DateField()


class DayStatusResultSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=DayStatus.choices, allow_null=True)
    entry_event = AttendanceEventSerializer(allow_null=True)


class AttendanceEventResolutionQuerySerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    shift_id = serializers.UUIDField()
    event_date = serializers.DateField()
    movement_type = serializers.ChoiceField(choices=AttendanceEvent.MovementType.choices)


class AttendanceAlertSerializer(serializers.ModelSerializer):
    student_id = serializers.UUIDField(source="student.public_id", read_only=True)
    shift_id = serializers.UUIDField(source="shift.public_id", read_only=True)
    section_id = serializers.UUIDField(
        source="section.public_id", read_only=True, allow_null=True
    )

    class Meta:
        model = AttendanceAlert
        fields = [
            "public_id",
            "alert_type",
            "student_id",
            "shift_id",
            "section_id",
            "event_date",
            "target_roles",
            "context",
            "created_at",
        ]


class JornadaClosureRequestSerializer(serializers.Serializer):
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada (Shift).")
    event_date = serializers.DateField(help_text="Fecha de la jornada a cerrar.")


class StudentJornadaClosureStatusSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(source="student.public_id")
    status = serializers.ChoiceField(choices=DayStatus.choices, allow_null=True)
    entry_event = AttendanceEventSerializer(allow_null=True)
    exit_event = AttendanceEventSerializer(allow_null=True)
    permanence_without_closure = serializers.BooleanField()


class JornadaClosureResultSerializer(serializers.Serializer):
    shift_id = serializers.UUIDField(source="shift.public_id")
    event_date = serializers.DateField()
    statuses = StudentJornadaClosureStatusSerializer(many=True)
    alerts = AttendanceAlertSerializer(many=True)
