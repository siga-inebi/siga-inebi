from rest_framework import serializers

from apps.attendance.models import (
    AttendanceAlert,
    AttendanceEvent,
    ControlPoint,
    DayStatus,
    JornadaParameters,
    ManualRegistrationReason,
    StudentCredential,
)


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
    control_point_id = serializers.UUIDField(
        source="control_point.public_id", read_only=True, allow_null=True
    )
    operator_id = serializers.IntegerField(source="operator.pk", read_only=True, allow_null=True)
    manual_reason_id = serializers.UUIDField(
        source="manual_reason.public_id", read_only=True, allow_null=True
    )

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
            "control_point_id",
            "operator_id",
            "manual_reason_id",
            "client_event_id",
            "batch_id",
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
    manual_reason_id = serializers.UUIDField(
        required=False,
        help_text=(
            "Public ID del motivo (ManualRegistrationReason). Obligatorio cuando "
            "origin=manual; se ignora para los demas origenes."
        ),
    )


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
    section_id = serializers.UUIDField(source="section.public_id", read_only=True, allow_null=True)

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


class AttendancePresenceQuerySerializer(serializers.Serializer):
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada (Shift).")
    event_date = serializers.DateField(
        required=False, help_text="Fecha a consultar; por omision, hoy."
    )
    grade_id = serializers.UUIDField(required=False, help_text="Filtro opcional por grado.")
    section_id = serializers.UUIDField(required=False, help_text="Filtro opcional por seccion.")


class PresentStudentSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(source="student.public_id")
    section_id = serializers.UUIDField(source="section.public_id")
    entry_event = AttendanceEventSerializer(allow_null=True)


class AttendancePercentageQuerySerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    shift_id = serializers.UUIDField()
    as_of_date = serializers.DateField(
        required=False, help_text="Fecha de corte; por omision, hoy."
    )


class AttendancePercentageResultSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(source="student.public_id")
    shift_id = serializers.UUIDField(source="shift.public_id")
    academic_cycle_id = serializers.UUIDField(source="academic_cycle.public_id")
    as_of_date = serializers.DateField()
    elapsed_school_days = serializers.IntegerField()
    present_days = serializers.IntegerField()
    late_days = serializers.IntegerField()
    percentage = serializers.FloatField(allow_null=True)


class ControlPointSerializer(serializers.ModelSerializer):
    campus_id = serializers.UUIDField(source="campus.public_id", read_only=True)

    class Meta:
        model = ControlPoint
        fields = ["public_id", "name", "code", "campus_id", "is_active"]


class ManualRegistrationReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManualRegistrationReason
        fields = ["public_id", "name", "code", "is_active"]


class ScanCaptureItemSerializer(serializers.Serializer):
    """
    One captured movement.

    The subject arrives either as the credential's opaque identifier
    (RF-CRE-006, what a real QR carries) or as ``student_code``, the fallback
    that predates the credential. Exactly one is required: accepting both would
    leave two answers for "who was scanned" and no rule for disagreement.
    """

    client_event_id = serializers.CharField(
        max_length=100, help_text="Id unico generado por el cliente."
    )
    credential_identifier = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        default="",
        help_text="Identificador opaco leido del codigo QR de la credencial.",
    )
    student_code = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        default="",
        help_text="Codigo estudiantil; alternativa al identificador de credencial.",
    )
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada (Shift).")
    control_point_id = serializers.UUIDField(help_text="Public ID del punto de control.")
    movement_type = serializers.ChoiceField(choices=AttendanceEvent.MovementType.choices)
    captured_at = serializers.DateTimeField(help_text="Hora de captura del escaneo.")

    def validate(self, attrs):
        identifies = [
            bool(attrs.get("credential_identifier")),
            bool(attrs.get("student_code")),
        ]
        if sum(identifies) != 1:
            raise serializers.ValidationError(
                "Se requiere credential_identifier o student_code, exactamente uno."
            )
        return attrs


class ScanCaptureRequestSerializer(serializers.Serializer):
    batch_id = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
        help_text="Id de agrupacion del lote; vacio para un escaneo individual.",
    )
    items = ScanCaptureItemSerializer(many=True, allow_empty=False)


class ScanCaptureItemResultSerializer(serializers.Serializer):
    client_event_id = serializers.CharField()
    outcome = serializers.ChoiceField(
        choices=["created", "duplicate_suppressed", "already_processed", "rejected"]
    )
    event = AttendanceEventSerializer(allow_null=True)
    duplicate_of = AttendanceEventSerializer(allow_null=True)
    reason = serializers.CharField(allow_blank=True)


class StudentCredentialSerializer(serializers.ModelSerializer):
    """
    RF-CRE-001 issuance response.

    ``opaque_identifier`` is what the QR encodes and the only reason this
    payload exists: the caller needs the token to print the credential. It is
    returned by the issuance response alone — no listing exposes it, because a
    page of tokens is a page of usable passes.
    """

    student_id = serializers.UUIDField(source="student.public_id", read_only=True)

    class Meta:
        model = StudentCredential
        fields = [
            "public_id",
            "student_id",
            "opaque_identifier",
            "status",
            "issued_at",
            "is_active",
            "created_at",
        ]


class StudentCredentialIssueSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID del estudiante.")


class CredentialResolutionRequestSerializer(serializers.Serializer):
    opaque_identifier = serializers.CharField(
        max_length=64, help_text="Identificador opaco leido del codigo QR."
    )


class CredentialResolutionSerializer(serializers.Serializer):
    """
    RF-CRE-006 response: who the scanned credential belongs to.

    The operator needs enough to confirm the person in front of them and no
    more, so the payload carries identity and placement and stops there. The
    identifier is not echoed back: the caller already holds it, and repeating
    it only widens where it can be logged.
    """

    student_id = serializers.UUIDField(source="student.public_id")
    student_code = serializers.CharField(source="student.student_code")
    full_name = serializers.CharField(source="student.person.__str__")
    grade_id = serializers.UUIDField(source="enrolment.grade.public_id")
    section_id = serializers.UUIDField(source="enrolment.section.public_id")
    academic_cycle_id = serializers.UUIDField(source="enrolment.academic_cycle.public_id")
    credential_status = serializers.CharField(source="credential.status")
