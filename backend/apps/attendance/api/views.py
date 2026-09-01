"""
HTTP layer for Jornada Diaria y Estados.

Views only translate between HTTP and ``apps.attendance.services``; every
invariant lives there (AGENTS.md #8). ``DomainError`` becomes a 400 envelope
via ``config.api.exception_handler``, so no view here catches it.

These handlers are written by hand on ``GenericAPIView`` instead of the generic
list/create machinery, so drf-spectacular cannot infer their contract: it only
sees ``serializer_class`` and would document the paginated listings as a single
object and the write bodies with the read serializer. Every operation therefore
declares its contract with ``extend_schema``. Without that the published schema
lies, and anything generated from it (typed clients, SDKs) inherits the lie.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.attendance import queries, services
from apps.audit.services import record_sensitive_read
from apps.common.exceptions import AuthorizationError, DomainError
from apps.identity import services as identity_services
from apps.identity.scopes import authorized_student_queryset, can_access_student

from .serializers import (
    AttendanceAlertSerializer,
    AttendanceEventCreateSerializer,
    AttendanceEventResolutionQuerySerializer,
    AttendanceEventSerializer,
    AttendancePercentageQuerySerializer,
    AttendancePercentageResultSerializer,
    AttendancePresenceQuerySerializer,
    ControlPointSerializer,
    CredentialPrintContentQuerySerializer,
    CredentialPrintContentSerializer,
    CredentialResolutionRequestSerializer,
    CredentialResolutionSerializer,
    CredentialRevocationRequestSerializer,
    CredentialRevocationResultSerializer,
    DayStatusQuerySerializer,
    DayStatusResultSerializer,
    JornadaClosureRequestSerializer,
    JornadaClosureResultSerializer,
    JornadaParametersCreateSerializer,
    JornadaParametersSerializer,
    ManualRegistrationReasonSerializer,
    PresentStudentSerializer,
    ScanCaptureItemResultSerializer,
    ScanCaptureRequestSerializer,
    SectionClosureRequestSerializer,
    SectionClosureResultSerializer,
    StudentCredentialIssueSerializer,
    StudentCredentialSerializer,
)

CONFIGURE_PERMISSION = "attendance_jornada_configure"
STUDENT_VIEW_PERMISSION = "student_view_basic"


def _require_permission(request, codename):
    if not request.user.has_atomic_permission(codename):
        raise AuthorizationError("El actor no tiene el permiso requerido.")


# Provisional: one atomic permission per event origin. A separate
# attendance-capture effort owns the real scanning/ingestion workflow and may
# replace this mapping; this skeleton exists only so RF-JOR-002/003 have
# events to read (see tmp/attendance_basis.md).
ORIGIN_PERMISSIONS = queries.origin_permissions()
MOVEMENT_TYPE_PERMISSIONS = queries.movement_type_permissions()

TAGS = ["attendance: jornada"]


@extend_schema_view(
    get=extend_schema(
        summary="Listar parametros de jornada",
        description="Parametros vigentes e historicos por jornada y ciclo escolar.",
        tags=TAGS,
        responses={200: JornadaParametersSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Registrar parametros de jornada",
        description=(
            "Registra un juego nuevo de parametros. No reemplaza en el lugar: el "
            "anterior se conserva como historia y deja de estar vigente."
        ),
        tags=TAGS,
        request=JornadaParametersCreateSerializer,
        responses={201: JornadaParametersSerializer},
    ),
)
class JornadaParametersListCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = JornadaParametersSerializer

    def get_queryset(self):
        return queries.jornada_parameters()

    def get(self, request):
        _require_permission(request, CONFIGURE_PERMISSION)
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(JornadaParametersSerializer(page, many=True).data)

    def post(self, request):
        _require_permission(request, CONFIGURE_PERMISSION)
        serializer = JornadaParametersCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        shift = queries.shift_for_payload(payload.pop("shift_id"))
        academic_cycle = queries.academic_cycle_for_payload(payload.pop("academic_cycle_id"))
        parameters = services.set_jornada_parameters(
            shift=shift, academic_cycle=academic_cycle, actor=request.user, **payload
        )
        return Response(
            JornadaParametersSerializer(parameters).data, status=status.HTTP_201_CREATED
        )


@extend_schema_view(
    get=extend_schema(
        summary="Listar movimientos de asistencia",
        description=(
            "Entradas y salidas dentro del alcance del actor. Incluye los "
            "movimientos suprimidos por duplicado (`is_active=false`): el registro "
            "se conserva, no se borra."
        ),
        tags=TAGS,
        responses={200: AttendanceEventSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Registrar movimiento de asistencia",
        description="El permiso exigido depende del origen del movimiento.",
        tags=TAGS,
        request=AttendanceEventCreateSerializer,
        responses={201: AttendanceEventSerializer},
    ),
)
class AttendanceEventListCreateView(GenericAPIView):
    """Deliberately thin skeleton: see ``ORIGIN_PERMISSIONS`` above."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendanceEventSerializer

    def get_queryset(self):
        return queries.attendance_events(
            students=authorized_student_queryset(
                user=self.request.user, codename=STUDENT_VIEW_PERMISSION
            )
        )

    def get(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(AttendanceEventSerializer(page, many=True).data)

    def post(self, request):
        serializer = AttendanceEventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        identity_services.require_all_permissions(
            actor=request.user,
            permission_codenames=[
                ORIGIN_PERMISSIONS[payload["origin"]],
                MOVEMENT_TYPE_PERMISSIONS[payload["movement_type"]],
            ],
            denial_action="attendance.event.capture_denied",
            denial_resource="AttendanceEvent",
        )
        student = queries.student_for_payload(payload.pop("student_id"))
        shift = queries.shift_for_payload(payload.pop("shift_id"))
        is_manual = payload["origin"] == "manual"
        manual_reason_id = payload.pop("manual_reason_id", None)
        manual_reason = (
            queries.manual_reason_for_payload(manual_reason_id)
            if is_manual and manual_reason_id
            else None
        )
        event = services.record_attendance_event(
            student=student,
            shift=shift,
            actor=request.user,
            operator=request.user if is_manual else None,
            manual_reason=manual_reason,
            **payload,
        )
        return Response(AttendanceEventSerializer(event).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar el movimiento que prevalece",
        description=(
            "Devuelve el movimiento vigente para un estudiante, jornada, fecha y "
            "tipo de movimiento, aplicando las reglas de precedencia. 404 cuando no "
            "hay ninguno."
        ),
        tags=TAGS,
        parameters=[AttendanceEventResolutionQuerySerializer],
        responses={200: AttendanceEventSerializer},
    ),
)
class AttendanceEventResolutionView(GenericAPIView):
    """RF-JOR-003 contract: the event that prevails by precedence."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendanceEventSerializer

    def get(self, request):
        query = AttendanceEventResolutionQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        payload = query.validated_data
        student = queries.student_for_payload(payload["student_id"])
        shift = queries.shift_for_payload(payload["shift_id"])
        if not can_access_student(
            user=request.user, codename=STUDENT_VIEW_PERMISSION, student=student
        ):
            raise AuthorizationError(
                "El actor no tiene el permiso requerido o el alcance sobre el estudiante."
            )
        event = services.resolve_prevailing_event(
            student=student,
            shift=shift,
            event_date=payload["event_date"],
            movement_type=payload["movement_type"],
        )
        if event is None:
            raise queries.no_event_error()
        return Response(AttendanceEventSerializer(event).data)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar el estado del dia de un estudiante",
        description=(
            "Deriva el estado del dia a partir de los movimientos registrados. "
            "Responde `status: null` cuando no hay nada que derivar."
        ),
        tags=TAGS,
        parameters=[DayStatusQuerySerializer],
        responses={200: DayStatusResultSerializer},
    ),
)
class AttendanceDayStatusView(GenericAPIView):
    """RF-JOR-002 contract: derive a student's daily status for a jornada."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DayStatusResultSerializer

    def get(self, request):
        query = DayStatusQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        payload = query.validated_data
        student = queries.student_for_payload(payload["student_id"])
        shift = queries.shift_for_payload(payload["shift_id"])
        if not can_access_student(
            user=request.user, codename=STUDENT_VIEW_PERMISSION, student=student
        ):
            raise AuthorizationError(
                "El actor no tiene el permiso requerido o el alcance sobre el estudiante."
            )
        record_sensitive_read(
            actor=request.user,
            action="attendance.day_status.read",
            resource="Student",
            resource_identifier=str(student.pk),
            student=student,
        )
        result = services.derive_day_status(
            student=student, shift=shift, event_date=payload["event_date"]
        )
        if result is None:
            return Response({"status": None, "entry_event": None})
        return Response(DayStatusResultSerializer(result).data)


@extend_schema_view(
    post=extend_schema(
        summary="Cerrar la jornada del dia",
        description=(
            "Recalcula los estados del dia y emite las alertas correspondientes. El "
            "cuerpo solo lleva jornada y fecha; los estados y alertas del resultado "
            "los calcula el servicio."
        ),
        tags=TAGS,
        request=JornadaClosureRequestSerializer,
        responses={200: JornadaClosureResultSerializer},
    ),
)
class JornadaClosureView(GenericAPIView):
    """RF-JOR-004 contract: run the daily closure for a jornada."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = JornadaClosureResultSerializer

    def post(self, request):
        _require_permission(request, CONFIGURE_PERMISSION)
        serializer = JornadaClosureRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        shift = queries.shift_for_payload(payload["shift_id"])
        result = services.close_jornada(
            shift=shift, event_date=payload["event_date"], actor=request.user
        )
        return Response(JornadaClosureResultSerializer(result).data)


def _require_declared_closure_permission(request):
    identity_services.require_all_permissions(
        actor=request.user,
        permission_codenames=[
            ORIGIN_PERMISSIONS["declared"],
            MOVEMENT_TYPE_PERMISSIONS["exit"],
        ],
        denial_action="attendance.event.capture_denied",
        denial_resource="AttendanceEvent",
    )


@extend_schema_view(
    get=extend_schema(
        summary="Previsualizar cierre declarado por seccion",
        description=(
            "RF-ASI-011: quien quedaria incluido y quien omitido -- y por que -- "
            "si se confirma el cierre declarado de la seccion, sin registrar nada "
            "todavia."
        ),
        tags=TAGS,
        responses={200: SectionClosureResultSerializer},
    ),
)
class SectionClosurePreviewView(GenericAPIView):
    """RF-ASI-011 contract: preview a section's declared closure."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SectionClosureResultSerializer

    def get(self, request):
        _require_declared_closure_permission(request)
        serializer = SectionClosureRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        section = queries.section_for_payload(payload["section_id"])
        result = services.preview_section_closure(section=section, event_date=payload["event_date"])
        return Response(SectionClosureResultSerializer(result).data)


@extend_schema_view(
    post=extend_schema(
        summary="Confirmar cierre declarado por seccion",
        description=(
            "RF-ASI-011: declara la salida de cada estudiante activamente "
            "inscrito en la seccion que tiene ingreso y aun no tiene salida "
            "registrada. Excluye a quien ya tiene salida registrada o no tiene "
            "ingreso, informando el motivo de cada exclusion."
        ),
        tags=TAGS,
        request=SectionClosureRequestSerializer,
        responses={200: SectionClosureResultSerializer},
    ),
)
class SectionClosureView(GenericAPIView):
    """RF-ASI-011 contract: confirm a section's declared closure."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SectionClosureResultSerializer

    def post(self, request):
        _require_declared_closure_permission(request)
        serializer = SectionClosureRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        section = queries.section_for_payload(payload["section_id"])
        result = services.close_section(
            section=section, event_date=payload["event_date"], actor=request.user
        )
        return Response(SectionClosureResultSerializer(result).data)


@extend_schema_view(
    get=extend_schema(
        summary="Listar alertas de asistencia",
        description="Alertas emitidas por el cierre de jornada, dentro del alcance del actor.",
        tags=TAGS,
        responses={200: AttendanceAlertSerializer(many=True)},
    ),
)
class AttendanceAlertListView(GenericAPIView):
    """RF-JOR-004/RF-JOR-005 contract: generated attendance alerts."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendanceAlertSerializer

    def get_queryset(self):
        return queries.attendance_alerts(
            students=authorized_student_queryset(
                user=self.request.user, codename=STUDENT_VIEW_PERMISSION
            )
        )

    def get(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(AttendanceAlertSerializer(page, many=True).data)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar presencia en tiempo real",
        description=(
            "Estudiantes con ingreso registrado y sin egreso posterior para una "
            "jornada y fecha, dentro del alcance del actor. Filtrable por grado y "
            "seccion."
        ),
        tags=TAGS,
        parameters=[AttendancePresenceQuerySerializer],
        responses={200: PresentStudentSerializer(many=True)},
    ),
)
class AttendancePresenceListView(GenericAPIView):
    """RF-JOR-008 contract: who is currently inside, in real time."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PresentStudentSerializer

    def get(self, request):
        query = AttendancePresenceQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        payload = query.validated_data
        shift = queries.shift_for_payload(payload["shift_id"])
        grade = queries.grade_for_payload(payload["grade_id"]) if payload.get("grade_id") else None
        section = (
            queries.section_for_payload(payload["section_id"])
            if payload.get("section_id")
            else None
        )
        authorized_students = authorized_student_queryset(
            user=request.user, codename=STUDENT_VIEW_PERMISSION
        )
        present = services.list_present_students(
            shift=shift,
            event_date=payload.get("event_date"),
            grade=grade,
            section=section,
            students=authorized_students,
        )
        page = self.paginate_queryset(present)
        return self.get_paginated_response(PresentStudentSerializer(page, many=True).data)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar porcentaje de asistencia del ciclo",
        description=(
            "Porcentaje de dias lectivos con presente o tarde sobre los dias "
            "lectivos transcurridos desde el inicio de la matricula activa del "
            "estudiante en el ciclo vigente."
        ),
        tags=TAGS,
        parameters=[AttendancePercentageQuerySerializer],
        responses={200: AttendancePercentageResultSerializer},
    ),
)
class AttendancePercentageView(GenericAPIView):
    """RF-JOR-009 contract: attendance-percentage indicator for the cycle."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendancePercentageResultSerializer

    def get(self, request):
        query = AttendancePercentageQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        payload = query.validated_data
        student = queries.student_for_payload(payload["student_id"])
        shift = queries.shift_for_payload(payload["shift_id"])
        if not can_access_student(
            user=request.user, codename=STUDENT_VIEW_PERMISSION, student=student
        ):
            raise AuthorizationError(
                "El actor no tiene el permiso requerido o el alcance sobre el estudiante."
            )
        record_sensitive_read(
            actor=request.user,
            action="attendance.percentage.read",
            resource="Student",
            resource_identifier=str(student.pk),
            student=student,
        )
        result = services.compute_attendance_percentage(
            student=student, shift=shift, as_of_date=payload.get("as_of_date")
        )
        return Response(AttendancePercentageResultSerializer(result).data)


@extend_schema_view(
    get=extend_schema(
        summary="Listar puntos de control",
        description="Catalogo de puntos de control por campus. Alta y edicion por Django admin.",
        tags=TAGS,
        responses={200: ControlPointSerializer(many=True)},
    ),
)
class ControlPointListView(GenericAPIView):
    """Read-only reference catalogue consumed by the scan-capture screen."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ControlPointSerializer

    def get_queryset(self):
        return queries.control_points()

    def get(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(ControlPointSerializer(page, many=True).data)


@extend_schema_view(
    get=extend_schema(
        summary="Listar motivos de registro manual",
        description=(
            "Catalogo configurable de motivos para un registro manual (RF-ASI-012). "
            "Alta y edicion por Django admin."
        ),
        tags=TAGS,
        responses={200: ManualRegistrationReasonSerializer(many=True)},
    ),
)
class ManualRegistrationReasonListView(GenericAPIView):
    """Read-only reference catalogue consumed by the manual-registration form."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ManualRegistrationReasonSerializer

    def get_queryset(self):
        return queries.manual_registration_reasons()

    def get(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(ManualRegistrationReasonSerializer(page, many=True).data)


@extend_schema_view(
    post=extend_schema(
        summary="Registrar movimientos por escaneo",
        description=(
            "Captura mediada por operador (RF-ASI-001). Cada elemento porta su "
            "propio `client_event_id`; reenviar el mismo id es un no-op exitoso "
            "(RF-ASI-010). Un elemento del mismo tipo/estudiante/jornada dentro de "
            "la ventana de supresion configurada se rechaza sin crear movimiento "
            "(RF-ASI-004). Un elemento invalido no aborta el resto del lote."
        ),
        tags=TAGS,
        request=ScanCaptureRequestSerializer,
        responses={200: ScanCaptureItemResultSerializer(many=True)},
    ),
)
class AttendanceScanView(GenericAPIView):
    """RF-ASI-002 contract: register movements captured by scanning."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ScanCaptureItemResultSerializer

    def post(self, request):
        _require_permission(request, "attendance_scan")
        serializer = ScanCaptureRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        batch_id = payload["batch_id"]
        raw_items = payload["items"]
        transmission = queries.scan_transmission(batch_id=batch_id, item_count=len(raw_items))

        resolved = []
        results_by_index = {}
        for index, raw_item in enumerate(raw_items):
            try:
                identity_services.require_all_permissions(
                    actor=request.user,
                    permission_codenames=[
                        ORIGIN_PERMISSIONS["scan"],
                        MOVEMENT_TYPE_PERMISSIONS[raw_item["movement_type"]],
                    ],
                    denial_action="attendance.event.capture_denied",
                    denial_resource="AttendanceEvent",
                )
                student = services.resolve_scan_subject(
                    credential_identifier=raw_item.get("credential_identifier", ""),
                    student_code=raw_item.get("student_code", ""),
                    actor=request.user,
                )
                shift = queries.shift_for_payload(raw_item["shift_id"])
                control_point = queries.control_point_for_payload(raw_item["control_point_id"])
            except (DomainError, AuthorizationError) as exc:
                results_by_index[index] = services.RejectedScanItem(
                    client_event_id=raw_item["client_event_id"], reason=str(exc)
                )
                continue
            resolved.append(
                (
                    index,
                    {
                        "student": student,
                        "shift": shift,
                        "control_point": control_point,
                        "movement_type": raw_item["movement_type"],
                        "captured_at": raw_item["captured_at"],
                        "client_event_id": raw_item["client_event_id"],
                        "batch_id": batch_id,
                        "transmission": transmission,
                    },
                )
            )

        outcomes = services.record_scan_batch(
            items=[item for _, item in resolved], operator=request.user, actor=request.user
        )
        for (index, _), outcome in zip(resolved, outcomes, strict=True):
            results_by_index[index] = outcome

        data = [
            {
                "client_event_id": result.client_event_id,
                "outcome": result.outcome,
                "event": getattr(result, "event", None),
                "duplicate_of": getattr(result, "duplicate_of", None),
                "confirmation": getattr(result, "confirmation", None),
                "reason": getattr(result, "reason", ""),
            }
            for result in (results_by_index[i] for i in range(len(raw_items)))
        ]
        return Response(ScanCaptureItemResultSerializer(data, many=True).data)


CREDENTIAL_TAGS = ["attendance: credencial"]
CREDENTIAL_ISSUE_PERMISSION = "attendance_credential_issue"
CREDENTIAL_RESOLVE_PERMISSION = "attendance_credential_resolve"


@extend_schema_view(
    post=extend_schema(
        summary="Emitir credencial de estudiante",
        tags=CREDENTIAL_TAGS,
        request=StudentCredentialIssueSerializer,
        responses={201: StudentCredentialSerializer},
    ),
)
class StudentCredentialIssueView(GenericAPIView):
    """Emitir identificador opaco para una credencial estudiantil (RF-CRE-001)."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentCredentialSerializer

    def post(self, request):
        serializer = StudentCredentialIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = queries.student_for_payload(serializer.validated_data["student_id"])
        if not can_access_student(
            user=request.user, codename=CREDENTIAL_ISSUE_PERMISSION, student=student
        ):
            raise AuthorizationError(
                "El actor no tiene el permiso requerido o el alcance sobre el estudiante."
            )
        credential = services.issue_credential(student=student, actor=request.user)
        return Response(
            StudentCredentialSerializer(credential).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(
        summary="Contenido imprimible de la credencial",
        description=(
            "Nombre completo, fotografia, grado, seccion, ciclo escolar e "
            "institucion para el material imprimible de la credencial "
            "(RF-CRE-002). No incluye salud, contacto de familia ni domicilio."
        ),
        tags=CREDENTIAL_TAGS,
        parameters=[CredentialPrintContentQuerySerializer],
        responses={200: CredentialPrintContentSerializer},
    ),
)
class CredentialPrintContentView(GenericAPIView):
    """RF-CRE-002 contract: exactly what the printed credential material shows."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CredentialPrintContentSerializer

    def get(self, request):
        query = CredentialPrintContentQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        student = queries.student_for_payload(query.validated_data["student_id"])
        if not can_access_student(
            user=request.user, codename=CREDENTIAL_ISSUE_PERMISSION, student=student
        ):
            raise AuthorizationError(
                "El actor no tiene el permiso requerido o el alcance sobre el estudiante."
            )
        content = services.resolve_credential_print_content(student=student)
        return Response(CredentialPrintContentSerializer(content).data)


@extend_schema_view(
    post=extend_schema(
        summary="Revocar credencial",
        description=(
            "Revoca de inmediato la credencial vigente del estudiante, indicando "
            "el motivo (RF-CRE-003). Una credencial revocada queda inutilizable "
            "para registrar movimientos."
        ),
        tags=CREDENTIAL_TAGS,
        request=CredentialRevocationRequestSerializer,
        responses={200: CredentialRevocationResultSerializer},
    ),
)
class CredentialRevocationView(GenericAPIView):
    """RF-CRE-003 contract: revoke a student's active credential."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CredentialRevocationResultSerializer

    def post(self, request):
        serializer = CredentialRevocationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        student = queries.student_for_payload(payload["student_id"])
        if not can_access_student(
            user=request.user, codename=CREDENTIAL_ISSUE_PERMISSION, student=student
        ):
            raise AuthorizationError(
                "El actor no tiene el permiso requerido o el alcance sobre el estudiante."
            )
        credential = services.revoke_credential(
            student=student, reason=payload["reason"], actor=request.user
        )
        return Response(CredentialRevocationResultSerializer(credential).data)


@extend_schema_view(
    post=extend_schema(
        summary="Resolver identificador de credencial",
        tags=CREDENTIAL_TAGS,
        request=CredentialResolutionRequestSerializer,
        responses={200: CredentialResolutionSerializer},
    ),
)
class StudentCredentialResolutionView(GenericAPIView):
    """Resolver QR opaco sin exponer el identificador en URL (RF-CRE-006)."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CredentialResolutionSerializer

    def post(self, request):
        _require_permission(request, CREDENTIAL_RESOLVE_PERMISSION)
        serializer = CredentialResolutionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resolution = services.resolve_credential(
            opaque_identifier=serializer.validated_data["opaque_identifier"],
            actor=request.user,
        )
        record_sensitive_read(
            actor=request.user,
            action="attendance.credential.resolved",
            resource="StudentCredential",
            resource_identifier=str(resolution.credential.public_id),
            student=resolution.student,
        )
        return Response(CredentialResolutionSerializer(resolution).data)
