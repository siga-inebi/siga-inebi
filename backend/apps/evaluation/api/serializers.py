"""
API serializers for evaluation domain.

Contracts for POST/PATCH operations. Validation happens here before calling services.
"""

import csv
import io

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from apps.academics.models import AcademicCycle, Section, Subject
from apps.enrolments.models import Enrolment
from apps.evaluation.models import (
    GRADE_MAX_VALUE,
    GRADE_MIN_VALUE,
    CaptureExceptionGrant,
    CycleEvaluationConfig,
    EvaluationGlobalConfig,
    EvaluationUnit,
    Grade,
    RecoveryGrade,
)
from apps.evaluation.services import GRADE_SHEET_MAX_ROWS
from apps.people.models import Person


class StudentSummarySerializer(serializers.Serializer):
    """Nombre del estudiante para pintar una fila sin otro catálogo (docs/ux-ui.md 1.1)."""

    public_id = serializers.UUIDField(read_only=True)
    student_code = serializers.CharField(read_only=True)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, student) -> str:
        return f"{student.person.first_name} {student.person.last_name}".strip()


class SectionReferenceSerializer(serializers.Serializer):
    public_id = serializers.UUIDField(read_only=True)
    name = serializers.SerializerMethodField()

    def get_name(self, section) -> str:
        return str(section)


class SubjectReferenceSerializer(serializers.Serializer):
    public_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


class PersonReferenceSerializer(serializers.Serializer):
    """Identificador opaco y nombre visible; sin datos de contacto (cf. PersonSerializer)."""

    public_id = serializers.UUIDField(read_only=True)
    name = serializers.SerializerMethodField()

    def get_name(self, person) -> str:
        return str(person)


class EvaluationUnitSerializer(serializers.ModelSerializer):
    """Read and write evaluation units via REST API."""

    public_id = serializers.UUIDField(read_only=True)
    academic_cycle_id = serializers.UUIDField(source="academic_cycle.public_id", read_only=True)
    # Opcionales al crear: las dos o ninguna (create_evaluation_unit). Después
    # se cambian con su propia acción, recovery-window/.
    recovery_starts_on = serializers.DateField(required=False, allow_null=True)
    recovery_ends_on = serializers.DateField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = EvaluationUnit
        fields = [
            "public_id",
            "academic_cycle",
            "academic_cycle_id",
            "number",
            "name",
            "starts_on",
            "ends_on",
            "capture_starts_on",
            "capture_ends_on",
            "recovery_starts_on",
            "recovery_ends_on",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "academic_cycle",
            "public_id",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        """Validate date ranges before passing to service."""
        if data["starts_on"] > data["ends_on"]:
            raise serializers.ValidationError(
                {
                    "ends_on": (
                        "La fecha de fin de la evaluacion no puede ser anterior a la de inicio."
                    )
                }
            )
        if data["capture_starts_on"] > data["capture_ends_on"]:
            raise serializers.ValidationError(
                {
                    "capture_ends_on": (
                        "La fecha de fin de la ventana de captura no puede ser anterior a "
                        "la de inicio."
                    )
                }
            )
        recovery_starts_on = data.get("recovery_starts_on")
        recovery_ends_on = data.get("recovery_ends_on")
        if recovery_starts_on and recovery_ends_on and recovery_starts_on > recovery_ends_on:
            raise serializers.ValidationError(
                {
                    "recovery_ends_on": (
                        "La fecha de fin de la ventana de recuperación no puede ser anterior "
                        "a la de inicio."
                    )
                }
            )
        return data


class RecoveryWindowSerializer(serializers.Serializer):
    """Contract for configuring a unit's recovery window (RF-EVC-003)."""

    recovery_starts_on = serializers.DateField()
    recovery_ends_on = serializers.DateField()

    def validate(self, data):
        if data["recovery_starts_on"] > data["recovery_ends_on"]:
            raise serializers.ValidationError(
                {
                    "recovery_ends_on": (
                        "La fecha de fin de la ventana de recuperacion no puede ser anterior "
                        "a la de inicio."
                    )
                }
            )
        return data


class CaptureExceptionGrantSerializer(serializers.ModelSerializer):
    """Contract for granting an exceptional capture window (RF-EVC-004)."""

    public_id = serializers.UUIDField(read_only=True)
    # Opaque identifiers, like the rest of the API: internal primary keys are
    # never part of the contract (docs/architecture/api-conventions.md, and the
    # explicit note on PersonSerializer). Clients that only ever see public_id
    # can also build a picker from any listing endpoint.
    subject = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Subject.objects.all(),
        help_text="Public ID de la subarea alcanzada por la excepcion.",
    )
    teacher = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Person.objects.all(),
        help_text="Public ID de la persona docente autorizada.",
    )
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CaptureExceptionGrant
        fields = [
            "public_id",
            "evaluation_unit",
            "subject",
            "teacher",
            "reason",
            "expires_at",
            "created_at",
        ]
        read_only_fields = ["public_id", "evaluation_unit", "created_at"]


class EvaluationGlobalConfigSerializer(serializers.ModelSerializer):
    """Contract for the institution-wide evaluation configuration (RF-EVC-005)."""

    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = EvaluationGlobalConfig
        fields = ["default_unit_count", "updated_at"]

    def validate_default_unit_count(self, value):
        if value <= 0:
            raise serializers.ValidationError("default_unit_count debe ser un entero positivo.")
        return value


class CycleEvaluationConfigSerializer(serializers.ModelSerializer):
    """Contract for a cycle's evaluation configuration override (RF-EVC-005)."""

    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CycleEvaluationConfig
        fields = ["unit_count", "updated_at"]

    def validate_unit_count(self, value):
        if value <= 0:
            raise serializers.ValidationError("unit_count debe ser un entero positivo.")
        return value


class CloneCycleEvaluationConfigSerializer(serializers.Serializer):
    """Contract for cloning a cycle's evaluation configuration (RF-EVC-006)."""

    target_cycle = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=AcademicCycle.objects.all(),
        help_text="Public ID del ciclo en preparacion que recibe la configuracion clonada.",
    )


@extend_schema_serializer(component_name="UnitGrade")
class GradeSerializer(serializers.ModelSerializer):
    """
    Contract for registering a unit grade (RF-CAL-001, RF-CAL-002).

    ``student``, ``subject_detail`` and ``evaluation_unit_id`` are read-only
    additions (V2, V5): ``enrolment``, ``subject`` and ``evaluation_unit`` keep
    their shape. ``subject_detail`` carries the name because ``subject`` is
    already the public_id. The component is published as ``UnitGrade`` so it
    no longer collides with the academics ``Grade`` (grado).
    """

    public_id = serializers.UUIDField(read_only=True)
    # Ver la nota de CaptureExceptionGrantSerializer: identificadores opacos.
    enrolment = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Enrolment.objects.all(),
        help_text="Public ID de la matricula a la que pertenece la nota.",
    )
    subject = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Subject.objects.all(),
        help_text="Public ID de la subarea calificada.",
    )
    teacher = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Person.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
        help_text=(
            "Public ID de la persona docente que captura. Opcional: sin él se toma "
            "el docente de la asignación vigente de la sección y la subárea."
        ),
    )
    student = StudentSummarySerializer(source="enrolment.student", read_only=True)
    subject_detail = SubjectReferenceSerializer(source="subject", read_only=True)
    evaluation_unit_id = serializers.UUIDField(source="evaluation_unit.public_id", read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Grade
        fields = [
            "public_id",
            "enrolment",
            "student",
            "subject",
            "subject_detail",
            "evaluation_unit",
            "evaluation_unit_id",
            "teacher",
            "value",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["public_id", "evaluation_unit", "created_at", "updated_at"]

    def validate_value(self, value):
        """RF-CAL-002: reject values outside the 0-100 scale."""
        if value < GRADE_MIN_VALUE or value > GRADE_MAX_VALUE:
            raise serializers.ValidationError(
                f"La nota debe estar entre {GRADE_MIN_VALUE} y {GRADE_MAX_VALUE}."
            )
        return value


class RecoveryEligibilitySerializer(serializers.Serializer):
    """Read-only contract for the recovery-eligibility check (RF-RES-004)."""

    enrolment_id = serializers.UUIDField(read_only=True)
    eligible = serializers.BooleanField(read_only=True)
    reasons = serializers.ListField(child=serializers.CharField(), read_only=True)
    attendance_percentage = serializers.FloatField(read_only=True, allow_null=True)
    failed_subjects = serializers.IntegerField(read_only=True)
    total_subjects = serializers.IntegerField(read_only=True)
    failed_limit = serializers.IntegerField(read_only=True)
    recovery_already_used = serializers.BooleanField(read_only=True)


class RecoveryGradeSerializer(serializers.ModelSerializer):
    """Contract for registering a recovery grade (RF-RES-005)."""

    public_id = serializers.UUIDField(read_only=True)
    # Ver la nota de CaptureExceptionGrantSerializer: identificadores opacos.
    subject = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Subject.objects.all(),
        help_text="Public ID de la subarea reprobada que se recupera.",
    )
    # Condicion recalculada de la subarea tras la recuperacion; la agrega la
    # vista a partir de get_final_subject_grade, no es un campo del modelo.
    condition = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_condition(self, obj) -> str | None:
        return getattr(obj, "recovery_condition", None)

    class Meta:
        model = RecoveryGrade
        fields = [
            "public_id",
            "subject",
            "value",
            "original_final_grade",
            "condition",
            "created_at",
        ]
        read_only_fields = ["public_id", "original_final_grade", "created_at"]

    def validate_value(self, value):
        """RF-CAL-002 scale, shared with unit grades: reject values outside 0-100."""
        if value < GRADE_MIN_VALUE or value > GRADE_MAX_VALUE:
            raise serializers.ValidationError(
                f"La nota debe estar entre {GRADE_MIN_VALUE} y {GRADE_MAX_VALUE}."
            )
        return value


class CaptureProgressRowSerializer(serializers.Serializer):
    """One (section, subarea) line of the capture-progress panel (RF-CAL-008)."""

    section = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    teacher = serializers.SerializerMethodField()
    students_total = serializers.IntegerField(read_only=True)
    students_graded = serializers.IntegerField(read_only=True)
    students_pending = serializers.IntegerField(read_only=True)
    progress_pct = serializers.FloatField(read_only=True)

    @extend_schema_field(SectionReferenceSerializer)
    def get_section(self, obj):
        section = obj["section"]
        return {"public_id": str(section.public_id), "name": str(section)}

    @extend_schema_field(SubjectReferenceSerializer)
    def get_subject(self, obj):
        subject = obj["subject"]
        return {"public_id": str(subject.public_id), "name": subject.name}

    @extend_schema_field(PersonReferenceSerializer(allow_null=True))
    def get_teacher(self, obj):
        # Opaque identifier plus a display name only: a progress panel does not
        # need the teacher's contact data (cf. PersonSerializer).
        teacher = obj["teacher"]
        if teacher is None:
            return None
        return {"public_id": str(teacher.public_id), "name": str(teacher)}


class CaptureProgressReportSerializer(serializers.Serializer):
    """Capture-progress panel for an evaluation unit (RF-CAL-008)."""

    unit_public_id = serializers.UUIDField(read_only=True)
    unit_name = serializers.CharField(read_only=True)
    window_open = serializers.BooleanField(read_only=True)
    overall_progress_pct = serializers.FloatField(read_only=True, allow_null=True)
    rows = CaptureProgressRowSerializer(many=True, read_only=True)


BULK_GRADE_MAX_BYTES = 2 * 1024 * 1024
BULK_GRADE_COLUMNS = ("student_code", "value")


class BulkGradeUploadSerializer(serializers.Serializer):
    """
    Contract for the bulk grade upload (RF-CAL-004).

    ``file`` is a CSV with a header row ``student_code,value`` and one data row
    per student. ``subject``, ``section`` and the optional ``teacher`` are
    opaque public IDs;
    the evaluation unit comes from the URL. Parsing the CSV into ``rows`` is done
    here (transport); every domain rule runs in bulk_register_unit_grades.
    """

    file = serializers.FileField(write_only=True)
    subject = serializers.SlugRelatedField(slug_field="public_id", queryset=Subject.objects.all())
    section = serializers.SlugRelatedField(slug_field="public_id", queryset=Section.objects.all())
    teacher = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Person.objects.all(),
        required=False,
        allow_null=True,
        help_text="Opcional: sin él se toma el docente de la asignación vigente (V8).",
    )

    def validate_file(self, uploaded):
        if uploaded.size > BULK_GRADE_MAX_BYTES:
            raise serializers.ValidationError(
                f"El archivo supera el maximo de {BULK_GRADE_MAX_BYTES} bytes."
            )
        try:
            text = uploaded.read().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise serializers.ValidationError("El archivo debe estar codificado en UTF-8.") from exc

        reader = csv.DictReader(io.StringIO(text))
        headers = [h.strip() for h in (reader.fieldnames or [])]
        missing = [column for column in BULK_GRADE_COLUMNS if column not in headers]
        if missing:
            raise serializers.ValidationError(
                f"Faltan columnas en el archivo: {', '.join(missing)}."
            )

        rows = [
            {
                "student_code": (row.get("student_code") or "").strip(),
                "value": (row.get("value") or "").strip(),
            }
            for row in reader
        ]
        if not rows:
            raise serializers.ValidationError("El archivo no contiene filas de datos.")
        self._parsed_rows = rows
        return uploaded

    def validate(self, attrs):
        attrs["rows"] = getattr(self, "_parsed_rows", [])
        return attrs


class GradeListFilterSerializer(serializers.Serializer):
    """Filtros opcionales del listado de notas de una unidad (V2)."""

    section_id = serializers.UUIDField(required=False)
    subject_id = serializers.UUIDField(required=False)
    student_id = serializers.UUIDField(required=False)


class GradeSheetQuerySerializer(serializers.Serializer):
    """Sección y subárea de la planilla de calificaciones (V2)."""

    section_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()


class GradeSheetGradeSerializer(serializers.Serializer):
    public_id = serializers.UUIDField(read_only=True)
    value = serializers.IntegerField(read_only=True)


class GradeSheetRowSerializer(serializers.Serializer):
    enrolment_id = serializers.UUIDField(source="enrolment.public_id", read_only=True)
    student = StudentSummarySerializer(source="enrolment.student", read_only=True)
    grade = GradeSheetGradeSerializer(read_only=True, allow_null=True)


class GradeSheetUnitSerializer(serializers.Serializer):
    public_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    window_open = serializers.BooleanField(read_only=True)


class GradeSheetSerializer(serializers.Serializer):
    """
    Planilla de calificaciones de una unidad, sección y subárea (V2, V8): todo
    lo que pinta la grilla en una sola llamada.
    """

    unit = serializers.SerializerMethodField()
    section = SectionReferenceSerializer(read_only=True)
    subject = SubjectReferenceSerializer(read_only=True)
    teacher = PersonReferenceSerializer(read_only=True, allow_null=True)
    rows = GradeSheetRowSerializer(many=True, read_only=True)

    @extend_schema_field(GradeSheetUnitSerializer)
    def get_unit(self, sheet):
        unit = sheet["unit"]
        return GradeSheetUnitSerializer(
            {
                "public_id": unit.public_id,
                "name": unit.name,
                "status": unit.status,
                "window_open": sheet["window_open"],
            }
        ).data


@extend_schema_field(OpenApiTypes.INT)
class RawGradeValueField(serializers.Field):
    """
    Pasa el valor tal cual: bulk_register_unit_grades lo valida por fila, así
    un valor inválido vuelve en ``errors`` con su índice como cualquier otro.
    """

    def to_internal_value(self, data):
        return data

    def to_representation(self, value):
        return value


class GradeSheetEntrySerializer(serializers.Serializer):
    enrolment_id = serializers.UUIDField(required=False, allow_null=True)
    student_code = serializers.CharField(required=False, allow_blank=True)
    value = RawGradeValueField(allow_null=True)


class GradeSheetSubmitSerializer(serializers.Serializer):
    """
    Guardado por lotes desde la planilla (V2): cada elemento identifica al
    estudiante por ``enrolment_id`` o ``student_code``. ``teacher_id`` es
    opcional (V8).
    """

    section_id = serializers.SlugRelatedField(
        slug_field="public_id", queryset=Section.objects.all()
    )
    subject_id = serializers.SlugRelatedField(
        slug_field="public_id", queryset=Subject.objects.all()
    )
    teacher_id = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Person.objects.all(),
        required=False,
        allow_null=True,
    )
    grades = GradeSheetEntrySerializer(
        many=True, allow_empty=False, max_length=GRADE_SHEET_MAX_ROWS
    )


class BulkGradeResultSerializer(serializers.Serializer):
    created = serializers.IntegerField(read_only=True)
    updated = serializers.IntegerField(read_only=True)


class GradeSheetErrorSerializer(serializers.Serializer):
    index = serializers.IntegerField(read_only=True)
    student_code = serializers.CharField(read_only=True, allow_null=True)
    field = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)


class GradeSheetErrorsSerializer(serializers.Serializer):
    errors = GradeSheetErrorSerializer(many=True, read_only=True)


class FailedSubjectSerializer(serializers.Serializer):
    public_id = serializers.UUIDField(source="subject.public_id", read_only=True)
    name = serializers.CharField(source="subject.name", read_only=True)
    final_grade = serializers.IntegerField(read_only=True, allow_null=True)


class SectionRecoveryEligibilitySerializer(serializers.Serializer):
    """
    Una fila del listado de elegibilidad de recuperación de una sección (V4).
    Aquí ``failed_subjects`` es la lista de subáreas reprobadas; el conteo
    está en ``failed_count`` (en el endpoint por matrícula, ``failed_subjects``
    sigue siendo el conteo).
    """

    enrolment_id = serializers.UUIDField(source="enrolment.public_id", read_only=True)
    student = StudentSummarySerializer(source="enrolment.student", read_only=True)
    eligible = serializers.BooleanField(source="eligibility.eligible", read_only=True)
    reasons = serializers.ListField(
        source="eligibility.reasons", child=serializers.CharField(), read_only=True
    )
    attendance_percentage = serializers.FloatField(
        source="eligibility.attendance_percentage", read_only=True, allow_null=True
    )
    failed_count = serializers.IntegerField(source="eligibility.failed_subjects", read_only=True)
    failed_limit = serializers.IntegerField(source="eligibility.failed_limit", read_only=True)
    recovery_already_used = serializers.BooleanField(
        source="eligibility.recovery_already_used", read_only=True
    )
    failed_subjects = FailedSubjectSerializer(
        source="eligibility.failed_subject_list", many=True, read_only=True
    )
