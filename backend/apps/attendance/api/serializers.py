from rest_framework import serializers

from apps.attendance.card_export import EXPORT_FORMATS, FORMAT_PNG, MAX_EXPORT_SIZE
from apps.attendance.models import (
    AbsenceNotification,
    AttendanceAlert,
    AttendanceEvent,
    AttendancePermit,
    CaptureBatch,
    ControlPoint,
    DayStatus,
    JornadaParameters,
    Justification,
    JustificationAttachment,
    JustificationNotification,
    JustificationReason,
    ManualRegistrationReason,
    StudentCredential,
)
from apps.common.qr import generate_qr_png_base64


class StudentReferenceSerializer(serializers.Serializer):
    """Nombre del estudiante para pintar una fila sin otro catálogo (docs/ux-ui.md 1.1)."""

    public_id = serializers.UUIDField(read_only=True)
    student_code = serializers.CharField(read_only=True)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, student) -> str:
        return f"{student.person.first_name} {student.person.last_name}".strip()


class AccountReferenceSerializer(serializers.Serializer):
    """Cuenta (``UserAccount.public_id``) y nombre de su persona; sin datos de contacto."""

    public_id = serializers.UUIDField(read_only=True)
    name = serializers.SerializerMethodField()

    def get_name(self, account) -> str:
        return str(account.person)


class CatalogueReferenceSerializer(serializers.Serializer):
    public_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


class ReviewQueueQuerySerializer(serializers.Serializer):
    """Filtros comunes de las bandejas de justificaciones y permisos (#631)."""

    student_id = serializers.UUIDField(required=False, help_text="Public ID del estudiante.")
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    search = serializers.CharField(
        required=False, allow_blank=True, help_text="Código o nombre del estudiante."
    )
    ordering = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        date_from, date_to = attrs.get("date_from"), attrs.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {"date_to": "La fecha final no puede ser anterior a la inicial."}
            )
        return attrs


class JornadaParametersSerializer(serializers.ModelSerializer):
    shift_id = serializers.UUIDField(source="shift.public_id", read_only=True)
    academic_cycle_id = serializers.UUIDField(source="academic_cycle.public_id", read_only=True)

    class Meta:
        model = JornadaParameters
        fields = [
            "public_id",
            "shift_id",
            "academic_cycle_id",
            "opening_time",
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
    opening_time = serializers.TimeField(
        required=False,
        help_text=(
            "Hora de apertura de la ventana operativa diaria (RF-JOR-001). "
            "Si se omite, la ventana abre a las 00:00."
        ),
    )
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


class AttendanceEventListQuerySerializer(serializers.Serializer):
    student_id = serializers.UUIDField(
        required=False, help_text="Filtra por UUID del estudiante antes de paginar."
    )


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


class AttendanceEventRowSerializer(AttendanceEventSerializer):
    """
    #631 (AS6): a movement as a listing row. ``student`` is additive so the
    staff UI names the student without downloading the whole roster; the
    write and nested responses keep ``AttendanceEventSerializer`` unchanged.
    """

    student = StudentReferenceSerializer(read_only=True)

    class Meta(AttendanceEventSerializer.Meta):
        fields = [*AttendanceEventSerializer.Meta.fields, "student"]


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


class AttendanceAlertRowSerializer(AttendanceAlertSerializer):
    """#631 (AS6): an alert as a listing row, with the student's name (additive)."""

    student = StudentReferenceSerializer(read_only=True)

    class Meta(AttendanceAlertSerializer.Meta):
        fields = [*AttendanceAlertSerializer.Meta.fields, "student"]


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


class SectionClosureRequestSerializer(serializers.Serializer):
    section_id = serializers.UUIDField(help_text="Public ID de la seccion.")
    event_date = serializers.DateField(help_text="Fecha de la jornada a cerrar.")
    confirmed = serializers.BooleanField(
        required=False,
        default=False,
        help_text=(
            "RF-ASI-013: obligatorio en `true` cuando quien declara no es el "
            "docente asignado a la seccion; de lo contrario no se registra nada "
            "y la respuesta trae confirmation_required=true."
        ),
    )


class SectionClosureStudentSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(source="public_id")


class SectionClosureOmissionSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(source="student.public_id")
    reason = serializers.CharField()


class SectionClosureResultSerializer(serializers.Serializer):
    """
    RF-ASI-011: who was (or would be) closed and who was omitted, and why --
    the same shape for the preview and for the confirmed closure, so a
    client renders both with one component.

    RF-ASI-013: ``is_covering`` and ``confirmation_required`` let the client
    show "estas cerrando como docente de cobertura, confirma para continuar"
    without a second round trip -- the same response already carries the
    section, grade and student counts needed for that prompt.
    """

    section_id = serializers.UUIDField(source="section.public_id")
    grade_name = serializers.CharField(source="section.offering.grade.name")
    event_date = serializers.DateField()
    included = SectionClosureStudentSerializer(many=True)
    omitted = SectionClosureOmissionSerializer(many=True)
    is_covering = serializers.BooleanField()
    confirmation_required = serializers.BooleanField()


class CoverageClosureRatioQuerySerializer(serializers.Serializer):
    section_id = serializers.UUIDField(required=False, help_text="Filtro opcional por seccion.")
    date_from = serializers.DateField(required=False, help_text="Fecha inicial, inclusive.")
    date_to = serializers.DateField(required=False, help_text="Fecha final, inclusive.")


class CoverageClosureRatioResultSerializer(serializers.Serializer):
    total_closures = serializers.IntegerField()
    covering_closures = serializers.IntegerField()
    coverage_ratio = serializers.FloatField(allow_null=True)


class AttendancePresenceQuerySerializer(serializers.Serializer):
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada (Shift).")
    event_date = serializers.DateField(
        required=False, help_text="Fecha a consultar; por omision, hoy."
    )
    grade_id = serializers.UUIDField(required=False, help_text="Filtro opcional por grado.")
    section_id = serializers.UUIDField(required=False, help_text="Filtro opcional por seccion.")


class PresentStudentSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(source="student.public_id")
    # #631 (AS6): additive, so the presence table names the student.
    student = StudentReferenceSerializer(read_only=True)
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
    regulatory_notice = serializers.CharField()


class ControlPointSerializer(serializers.ModelSerializer):
    campus_id = serializers.UUIDField(source="campus.public_id", read_only=True)

    class Meta:
        model = ControlPoint
        fields = [
            "public_id",
            "name",
            "code",
            "campus_id",
            "allows_entry",
            "allows_exit",
            "is_active",
        ]


class ManualRegistrationReasonListQuerySerializer(serializers.Serializer):
    # allow_null: a missing boolean in a QueryDict would otherwise read as False.
    is_active = serializers.BooleanField(
        required=False,
        allow_null=True,
        help_text="Por omisión, solo los motivos vigentes; `false` lista los retirados.",
    )


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
    capture_batch_id = serializers.UUIDField(
        required=False,
        help_text=(
            "Public ID del lote de captura recuperable (RF-ASI-009) al que "
            "pertenecen estos elementos; omitido para un escaneo fuera de un "
            "lote recuperable."
        ),
    )
    items = ScanCaptureItemSerializer(many=True, allow_empty=False)


class ScanConfirmationSerializer(serializers.Serializer):
    """
    RF-ASI-003: exclusively the fields the operator needs to confirm the
    person in front of them. No health, academic, contact or address data
    belongs here -- see ``services.ScanConfirmation``.
    """

    student_id = serializers.UUIDField(source="student.public_id")
    full_name = serializers.CharField()
    grade_name = serializers.CharField(allow_null=True)
    section_name = serializers.CharField(allow_null=True)
    photo_url = serializers.CharField(allow_null=True)


class ScanCaptureItemResultSerializer(serializers.Serializer):
    client_event_id = serializers.CharField()
    outcome = serializers.ChoiceField(
        choices=["created", "duplicate_suppressed", "already_processed", "rejected"]
    )
    event = AttendanceEventSerializer(allow_null=True)
    duplicate_of = AttendanceEventSerializer(allow_null=True)
    confirmation = ScanConfirmationSerializer(allow_null=True)
    reason = serializers.CharField(allow_blank=True)
    reason_code = serializers.ChoiceField(
        choices=["", "non_school_day", "outside_operating_window", "capture_batch_expired"],
        allow_blank=True,
        help_text=(
            "Causa estable de un rechazo: dia no lectivo o fuera de la ventana "
            "operativa (RF-JOR-001), turno de captura vencido (RF-AUT-005). "
            "Vacio para los demas resultados."
        ),
    )


class CaptureBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaptureBatch
        fields = ["public_id", "status", "confirmed_at", "expires_at", "created_at"]


class CaptureBatchRecoverySerializer(serializers.Serializer):
    """
    RF-ASI-009: what an operator gets back on recovery -- the batch itself
    (``null`` when there is nothing pending) plus every movement already
    saved in it, each with its original capture time intact.
    """

    capture_batch = CaptureBatchSerializer(allow_null=True)
    events = AttendanceEventRowSerializer(many=True)


class StudentCredentialSerializer(serializers.ModelSerializer):
    """
    RF-CRE-001 issuance response.

    ``opaque_identifier`` is what the QR encodes and the only reason this
    payload exists: the caller needs the token to print the credential. It is
    returned by the issuance response alone — no listing exposes it, because a
    page of tokens is a page of usable passes.

    RNF-PRI-001: ``qr_code`` is the printable QR image, generated from
    ``opaque_identifier`` alone via ``generate_qr_png_base64`` -- that
    function only ever accepts a plain string, never this serializer's
    instance, so nothing else this payload carries (``student_id`` included)
    can end up encoded in it.
    """

    student_id = serializers.UUIDField(source="student.public_id", read_only=True)
    qr_code = serializers.SerializerMethodField(
        help_text="Imagen PNG del codigo QR, en base64, codificando unicamente opaque_identifier."
    )

    class Meta:
        model = StudentCredential
        fields = [
            "public_id",
            "student_id",
            "opaque_identifier",
            "qr_code",
            "status",
            "issued_at",
            "is_active",
            "created_at",
        ]

    def get_qr_code(self, credential):
        return generate_qr_png_base64(data=credential.opaque_identifier)


class CredentialStatusSerializer(serializers.Serializer):
    """
    #631 (AS2): state of the student's latest credential. Never carries
    ``opaque_identifier`` nor the QR: see ``StudentCredentialSerializer``.
    """

    student_id = serializers.UUIDField()
    status = serializers.ChoiceField(
        choices=["active", "revoked", "none"],
        help_text="`none` cuando el estudiante nunca tuvo credencial.",
    )
    public_id = serializers.UUIDField(allow_null=True)
    issued_at = serializers.DateTimeField(allow_null=True)
    revoked_at = serializers.DateTimeField(allow_null=True)
    revocation_reason = serializers.CharField(allow_null=True)


class StudentCredentialIssueSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID del estudiante.")


class CredentialRevocationRequestSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID del estudiante.")
    reason = serializers.CharField(
        max_length=255, help_text="Motivo de la revocacion (extravio, retiro, etc.)."
    )


class CredentialRevocationResultSerializer(serializers.ModelSerializer):
    """
    RF-CRE-003 revocation response: confirms the credential is revoked, with
    its reason and who revoked it. Deliberately omits ``opaque_identifier`` --
    see ``StudentCredentialSerializer``'s docstring on why a token should
    never be echoed back outside the one response that issues it.
    """

    student_id = serializers.UUIDField(source="student.public_id", read_only=True)
    revoked_by_id = serializers.IntegerField(
        source="revoked_by.pk", read_only=True, allow_null=True
    )

    class Meta:
        model = StudentCredential
        fields = [
            "public_id",
            "student_id",
            "status",
            "revocation_reason",
            "revoked_by_id",
            "issued_at",
            "is_active",
            "updated_at",
        ]


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


class CredentialPrintContentQuerySerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID del estudiante.")


class CredentialPrintContentSerializer(serializers.Serializer):
    """
    RF-CRE-002 response: exactly what the printed/digital credential shows.

    Deliberately excludes everything else the student record carries (health,
    address, family contact) -- the field list itself is the boundary.
    """

    student_id = serializers.UUIDField(source="student.public_id")
    full_name = serializers.CharField()
    grade_name = serializers.CharField()
    section_name = serializers.CharField()
    academic_cycle_name = serializers.CharField()
    institution_name = serializers.CharField()
    photo_url = serializers.CharField(allow_null=True)


class CredentialQrRequestSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID del estudiante.")


class CredentialQrSerializer(serializers.Serializer):
    """
    Reimpresion del QR de la credencial vigente. Solo la imagen: el token en
    texto no viaja, igual que en el resto de respuestas fuera de la emision.
    """

    qr_code = serializers.CharField(
        help_text="Imagen PNG del codigo QR, en base64, codificando unicamente el identificador."
    )


class CredentialExportRequestSerializer(serializers.Serializer):
    student_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        max_length=MAX_EXPORT_SIZE,
        help_text=f"Public IDs de 1 a {MAX_EXPORT_SIZE} estudiantes distintos.",
    )
    format = serializers.ChoiceField(
        choices=EXPORT_FORMATS,
        help_text="`pdf` (carta, 8 por hoja), `png` (exactamente un estudiante) o `zip` de PNG.",
    )

    def validate_student_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Un estudiante no puede repetirse en el lote.")
        return value

    def validate(self, attrs):
        if attrs["format"] == FORMAT_PNG and len(attrs["student_ids"]) != 1:
            raise serializers.ValidationError(
                {"format": "El formato PNG exporta un solo carné; use PDF o ZIP para varios."}
            )
        return attrs


class CredentialExportRowSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    full_name = serializers.CharField(help_text="Vacio si el estudiante no existe o no es visible.")
    student_code = serializers.CharField()
    status = serializers.ChoiceField(choices=["ready", "to_issue", "skipped"])
    reason = serializers.CharField(allow_null=True)


class CredentialExportSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    ready = serializers.IntegerField()
    to_issue = serializers.IntegerField()
    skipped = serializers.IntegerField()


class CredentialExportPreviewSerializer(serializers.Serializer):
    summary = CredentialExportSummarySerializer()
    rows = CredentialExportRowSerializer(many=True)


class JustificationReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = JustificationReason
        fields = ["public_id", "name", "code"]


class JustificationRequestSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID del estudiante.")
    absence_date = serializers.DateField(help_text="Fecha de la inasistencia a justificar.")
    situation_type = serializers.ChoiceField(
        choices=Justification.SituationType.choices,
        required=False,
        default=Justification.SituationType.ABSENCE,
        help_text="RF-JUS-001: inasistencia o llegada tardia.",
    )
    reason = serializers.CharField(help_text="Motivo de la justificacion.")
    reason_catalog_id = serializers.UUIDField(
        required=False,
        help_text="RF-JUS-001: Public ID de un motivo del catalogo configurable (opcional).",
    )
    is_exception = serializers.BooleanField(
        required=False,
        default=False,
        help_text=(
            "RF-JUS-003: solo procesable por un usuario con "
            "attendance_justification_resolve. Registra la justificacion "
            "fuera de la ventana, documentando el motivo de la excepcion."
        ),
    )
    exception_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Obligatorio cuando is_exception es verdadero.",
    )


class JustificationListQuerySerializer(ReviewQueueQuerySerializer):
    status = serializers.ChoiceField(choices=Justification.Status.choices, required=False)


class JustificationSerializer(serializers.ModelSerializer):
    """
    #631 (AS3): the ``*_id`` fields stay as they were; ``student``,
    ``reason_catalog``, ``submitted_by``, ``resolved_by``, the ``*_display``
    labels, ``has_attachment`` and ``submitted_at`` are additive, so a row
    renders without another lookup.
    """

    student = StudentReferenceSerializer(read_only=True)
    reason_catalog = CatalogueReferenceSerializer(read_only=True, allow_null=True)
    submitted_by = AccountReferenceSerializer(read_only=True)
    resolved_by = AccountReferenceSerializer(read_only=True, allow_null=True)
    situation_type_display = serializers.CharField(
        source="get_situation_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    has_attachment = serializers.SerializerMethodField()
    submitted_at = serializers.DateTimeField(source="created_at", read_only=True)
    student_id = serializers.UUIDField(source="student.public_id", read_only=True)
    submitted_by_id = serializers.IntegerField(source="submitted_by.pk", read_only=True)
    reason_catalog_id = serializers.UUIDField(
        source="reason_catalog.public_id", read_only=True, allow_null=True
    )
    resolved_by_id = serializers.IntegerField(
        source="resolved_by.pk", read_only=True, allow_null=True
    )

    class Meta:
        model = Justification
        fields = [
            "public_id",
            "student_id",
            "student",
            "absence_date",
            "situation_type",
            "situation_type_display",
            "reason",
            "reason_catalog_id",
            "reason_catalog",
            "status",
            "status_display",
            "has_attachment",
            "submitted_by_id",
            "submitted_by",
            "submitted_at",
            "is_exception",
            "exception_reason",
            "resolved_by_id",
            "resolved_by",
            "resolved_at",
            "resolution_comment",
            "created_at",
        ]

    def get_has_attachment(self, justification) -> bool:
        # The queue annotates it (no query per row); a single instance asks.
        annotated = getattr(justification, "attachment_exists", None)
        if annotated is not None:
            return annotated
        return JustificationAttachment.objects.filter(justification=justification).exists()


class JustificationResolutionRequestSerializer(serializers.Serializer):
    approved = serializers.BooleanField(help_text="True para aprobar, False para rechazar.")
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Obligatorio al rechazar; opcional al aprobar.",
    )


class JustificationNotificationSerializer(serializers.ModelSerializer):
    justification_id = serializers.UUIDField(source="justification.public_id", read_only=True)
    student_id = serializers.UUIDField(source="justification.student.public_id", read_only=True)
    absence_date = serializers.DateField(source="justification.absence_date", read_only=True)
    status = serializers.CharField(source="justification.status", read_only=True)
    resolution_comment = serializers.CharField(
        source="justification.resolution_comment", read_only=True
    )
    resolved_at = serializers.DateTimeField(source="justification.resolved_at", read_only=True)

    class Meta:
        model = JustificationNotification
        fields = [
            "public_id",
            "justification_id",
            "student_id",
            "absence_date",
            "status",
            "resolution_comment",
            "resolved_at",
            "created_at",
        ]


class JustificationAttachmentSerializer(serializers.ModelSerializer):
    justification_id = serializers.UUIDField(source="justification.public_id", read_only=True)
    uploaded_by_id = serializers.IntegerField(source="uploaded_by.pk", read_only=True)

    class Meta:
        model = JustificationAttachment
        fields = [
            "public_id",
            "justification_id",
            "filename",
            "content_type",
            "size_bytes",
            "checksum",
            "uploaded_by_id",
            "created_at",
        ]


class JustificationAttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="Documento de respaldo (PDF/JPG/PNG).")


class AttendancePermitRequestSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID del estudiante.")
    permit_type = serializers.ChoiceField(
        choices=AttendancePermit.PermitType.choices,
        help_text="Salida anticipada o ingreso tardio.",
    )
    permit_date = serializers.DateField(help_text="Fecha para la que se solicita el permiso.")
    scheduled_time = serializers.TimeField(help_text="Horario previsto del hecho.")
    reason = serializers.CharField(help_text="Motivo del permiso.")


class AttendancePermitListQuerySerializer(ReviewQueueQuerySerializer):
    status = serializers.ChoiceField(choices=AttendancePermit.Status.choices, required=False)
    permit_type = serializers.ChoiceField(
        choices=AttendancePermit.PermitType.choices, required=False
    )


class AttendancePermitSerializer(serializers.ModelSerializer):
    """
    #631 (AS4): ``student``, ``submitted_by``, ``resolved_by``, the
    ``*_display`` labels and ``submitted_at`` are additive to the ``*_id``
    fields, also in the create and resolve responses.
    """

    student = StudentReferenceSerializer(read_only=True)
    submitted_by = AccountReferenceSerializer(read_only=True)
    resolved_by = AccountReferenceSerializer(read_only=True, allow_null=True)
    permit_type_display = serializers.CharField(source="get_permit_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    submitted_at = serializers.DateTimeField(source="created_at", read_only=True)
    student_id = serializers.UUIDField(source="student.public_id", read_only=True)
    submitted_by_id = serializers.IntegerField(source="submitted_by.pk", read_only=True)
    resolved_by_id = serializers.IntegerField(
        source="resolved_by.pk", read_only=True, allow_null=True
    )

    class Meta:
        model = AttendancePermit
        fields = [
            "public_id",
            "student_id",
            "student",
            "permit_type",
            "permit_type_display",
            "permit_date",
            "scheduled_time",
            "reason",
            "status",
            "status_display",
            "submitted_by_id",
            "submitted_by",
            "submitted_at",
            "resolved_by_id",
            "resolved_by",
            "resolved_at",
            "resolution_comment",
            "created_at",
        ]


class AttendancePermitResolutionRequestSerializer(serializers.Serializer):
    approved = serializers.BooleanField(help_text="True para aprobar, False para rechazar.")
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Obligatorio al rechazar; opcional al aprobar.",
    )


class AbsenceNotificationSerializer(serializers.ModelSerializer):
    """RF-JOR-007: an absence notification as the guardian sees it."""

    student_id = serializers.UUIDField(source="student.public_id", read_only=True)
    student_name = serializers.SerializerMethodField()
    shift_id = serializers.UUIDField(source="shift.public_id", read_only=True)
    is_superseded = serializers.SerializerMethodField()

    class Meta:
        model = AbsenceNotification
        fields = [
            "public_id",
            "student_id",
            "student_name",
            "shift_id",
            "absence_date",
            "reason",
            "is_superseded",
            "superseded_at",
            "created_at",
        ]

    def get_student_name(self, obj) -> str:
        person = obj.student.person
        return f"{person.first_name} {person.last_name}".strip()

    def get_is_superseded(self, obj) -> bool:
        return obj.superseded_at is not None
