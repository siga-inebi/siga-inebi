from rest_framework import serializers

from apps.academics.models import (
    AcademicCycle,
    Campus,
    ClassScheduleBlock,
    CurriculumPlan,
    Grade,
    GradeOffering,
    Level,
    LevelSubject,
    Section,
    Shift,
    Subject,
    TeachingAssignment,
)


class AcademicCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicCycle
        fields = [
            "public_id",
            "year",
            "name",
            "description",
            "starts_on",
            "ends_on",
            "status",
        ]


class AcademicCycleCreateSerializer(serializers.Serializer):
    """
    El anio es lo unico obligatorio.

    Nombre y vigencia se derivan de el (``apps.academics.school_calendar``), y
    pedirlos por separado solo abre la puerta a un "Ciclo 2026" cuyo anio dice
    2027. Se siguen aceptando porque un acuerdo ministerial puede mover el
    calendario.
    """

    year = serializers.IntegerField(min_value=1900, max_value=9999)
    name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text='Opcional. Por omision, "Ciclo <anio>".',
    )
    description = serializers.CharField(required=False, allow_blank=True)
    starts_on = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Opcional. Por omision, el 15 de enero corrido al siguiente dia habil.",
    )
    ends_on = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Opcional. Por omision, el 31 de octubre corrido al dia habil anterior.",
    )


class AcademicCycleDefaultsSerializer(serializers.Serializer):
    """Valores que tomaria un ciclo del anio consultado, sin crearlo."""

    year = serializers.IntegerField()
    name = serializers.CharField()
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()


class AcademicCycleCloneSerializer(AcademicCycleCreateSerializer):
    include_teaching_assignments = serializers.BooleanField(required=False, default=False)


# --------------------------------------------------------------------------- #
# compact references, used whenever a payload needs to name a catalogue node
# --------------------------------------------------------------------------- #


class CampusRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campus
        fields = ["public_id", "name", "code"]


class ShiftRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ["public_id", "name", "code"]


class LevelRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ["public_id", "name", "code", "sequence"]


class GradeRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = ["public_id", "name", "code", "sequence"]


class SubjectRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["public_id", "name", "code"]


# --------------------------------------------------------------------------- #
# campuses ("sedes")
# --------------------------------------------------------------------------- #


class CampusSerializer(serializers.ModelSerializer):
    """Every queryset that feeds this serializer annotates ``_shift_count``."""

    shift_count = serializers.IntegerField(source="_shift_count", read_only=True)

    class Meta:
        model = Campus
        fields = [
            "public_id",
            "name",
            "code",
            "address",
            "is_main",
            "is_active",
            "shift_count",
        ]


class CampusCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, help_text="Nombre visible de la sede.")
    code = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        help_text=(
            "Codigo corto, unico por institucion. Se normaliza a mayusculas. "
            'Opcional: vacio genera el siguiente de la serie ("SED-01").'
        ),
    )
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    is_main = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Marca la sede principal. Solo puede haber una por institucion.",
    )


class CampusUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    is_main = serializers.BooleanField(required=False)


# --------------------------------------------------------------------------- #
# shifts ("jornadas")
# --------------------------------------------------------------------------- #


class ShiftSerializer(serializers.ModelSerializer):
    campus = CampusRefSerializer(read_only=True)

    class Meta:
        model = Shift
        fields = ["public_id", "name", "code", "is_active", "campus"]


class ShiftCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, help_text="Ej. Matutina, Vespertina.")
    code = serializers.CharField(
        max_length=30,
        help_text="Codigo unico dentro de la sede. Se normaliza a mayusculas.",
    )


class ShiftUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)


# --------------------------------------------------------------------------- #
# schedule blocks ("rejilla de bloques")
# --------------------------------------------------------------------------- #


class ClassScheduleBlockSerializer(serializers.ModelSerializer):
    shift = ShiftRefSerializer(read_only=True)

    class Meta:
        model = ClassScheduleBlock
        fields = ["public_id", "number", "name", "starts_on", "ends_on", "is_active", "shift"]


class ClassScheduleBlockCreateSerializer(serializers.Serializer):
    number = serializers.IntegerField(
        min_value=1, help_text="Orden del bloque dentro de la jornada."
    )
    name = serializers.CharField(max_length=100, help_text='Ej. "Bloque 1", "Recreo".')
    starts_on = serializers.TimeField(help_text="Hora de inicio del bloque.")
    ends_on = serializers.TimeField(help_text="Hora de fin del bloque.")


class ClassScheduleBlockUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    starts_on = serializers.TimeField(required=False)
    ends_on = serializers.TimeField(required=False)


# --------------------------------------------------------------------------- #
# levels ("niveles")
# --------------------------------------------------------------------------- #


class LevelSerializer(serializers.ModelSerializer):
    """Querysets annotate ``_grade_count`` and ``_subject_count``."""

    grade_count = serializers.IntegerField(source="_grade_count", read_only=True)
    subject_count = serializers.IntegerField(source="_subject_count", read_only=True)

    class Meta:
        model = Level
        fields = [
            "public_id",
            "name",
            "code",
            "sequence",
            "is_active",
            "grade_count",
            "subject_count",
        ]


INSERT_AFTER_HELP = (
    "Posicion: identificador del hermano al que debe seguir. `null` lo pone "
    "primero; omitirlo lo pone al final. Los hermanos se renumeran solos."
)


class LevelCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, help_text="Ej. Preprimaria, Primaria, Basico.")
    code = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        help_text='Codigo unico por institucion. Opcional: vacio genera "NIV-01".',
    )
    sequence = serializers.IntegerField(
        min_value=1,
        required=False,
        help_text="Orden pedagogico explicito. Manda sobre `insert_after`.",
    )
    insert_after = serializers.UUIDField(
        required=False, allow_null=True, help_text=INSERT_AFTER_HELP
    )


class LevelUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    sequence = serializers.IntegerField(min_value=1, required=False)
    insert_after = serializers.UUIDField(
        required=False, allow_null=True, help_text=INSERT_AFTER_HELP
    )


class SuggestedCodeSerializer(serializers.Serializer):
    """Siguiente codigo libre de una serie, para prellenar un formulario."""

    code = serializers.CharField()


# --------------------------------------------------------------------------- #
# grades ("grados")
# --------------------------------------------------------------------------- #


class GradeSerializer(serializers.ModelSerializer):
    level = LevelRefSerializer(read_only=True)

    class Meta:
        model = Grade
        fields = ["public_id", "name", "code", "sequence", "is_active", "level"]


class GradeCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, help_text="Ej. Primero Primaria.")
    code = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        help_text=(
            'Codigo unico por institucion. Opcional: vacio lo deriva del codigo del nivel ("BAS1").'
        ),
    )
    sequence = serializers.IntegerField(
        min_value=1,
        required=False,
        help_text="Orden explicito dentro del nivel. Manda sobre `insert_after`.",
    )
    insert_after = serializers.UUIDField(
        required=False, allow_null=True, help_text=INSERT_AFTER_HELP
    )


class GradeUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    sequence = serializers.IntegerField(min_value=1, required=False)
    insert_after = serializers.UUIDField(
        required=False, allow_null=True, help_text=INSERT_AFTER_HELP
    )


# --------------------------------------------------------------------------- #
# subjects ("cursos") and their link to levels
# --------------------------------------------------------------------------- #


class SubjectSerializer(serializers.ModelSerializer):
    levels = LevelRefSerializer(many=True, read_only=True)

    class Meta:
        model = Subject
        fields = ["public_id", "name", "code", "is_active", "levels"]


class SubjectCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, help_text="Ej. Matematica.")
    code = serializers.CharField(max_length=50, help_text="Codigo unico por institucion.")


class SubjectUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)


class LevelSubjectSerializer(serializers.ModelSerializer):
    level = LevelRefSerializer(read_only=True)
    subject = SubjectRefSerializer(read_only=True)

    class Meta:
        model = LevelSubject
        fields = ["public_id", "level", "subject", "is_required", "weekly_hours"]


class LevelSubjectCreateSerializer(serializers.Serializer):
    subject_id = serializers.UUIDField(help_text="Public ID del curso a vincular.")
    is_required = serializers.BooleanField(required=False, default=True)
    weekly_hours = serializers.IntegerField(
        min_value=0, required=False, default=0, help_text="0 significa sin definir."
    )


class LevelSubjectUpdateSerializer(serializers.Serializer):
    is_required = serializers.BooleanField(required=False)
    weekly_hours = serializers.IntegerField(min_value=0, required=False)


# --------------------------------------------------------------------------- #
# sections ("secciones")
# --------------------------------------------------------------------------- #


class SectionSerializer(serializers.ModelSerializer):
    academic_cycle_id = serializers.UUIDField(
        source="offering.academic_cycle.public_id", read_only=True
    )
    grade = GradeRefSerializer(source="offering.grade", read_only=True)
    shift = ShiftRefSerializer(source="offering.shift", read_only=True)

    class Meta:
        model = Section
        fields = [
            "public_id",
            "name",
            "capacity",
            "is_active",
            "academic_cycle_id",
            "grade",
            "shift",
        ]


class SectionCreateSerializer(serializers.Serializer):
    academic_cycle_id = serializers.UUIDField(help_text="Public ID del ciclo escolar.")
    grade_id = serializers.UUIDField(help_text="Public ID del grado.")
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada.")
    name = serializers.CharField(max_length=50, help_text='Ej. "A", "B".')
    capacity = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0,
        help_text="Cupo maximo declarado. 0 significa sin limite.",
    )


class SectionUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50, required=False)
    capacity = serializers.IntegerField(min_value=0, required=False)


# --------------------------------------------------------------------------- #
# curriculum plans ("plan de estudios")
# --------------------------------------------------------------------------- #


class CurriculumPlanSerializer(serializers.ModelSerializer):
    academic_cycle_id = serializers.UUIDField(source="academic_cycle.public_id", read_only=True)
    grade = GradeRefSerializer(read_only=True)
    subject = SubjectRefSerializer(read_only=True)

    class Meta:
        model = CurriculumPlan
        fields = [
            "public_id",
            "is_required",
            "is_active",
            "academic_cycle_id",
            "grade",
            "subject",
        ]


class CurriculumPlanCreateSerializer(serializers.Serializer):
    academic_cycle_id = serializers.UUIDField(help_text="Public ID del ciclo escolar.")
    grade_id = serializers.UUIDField(help_text="Public ID del grado.")
    subject_id = serializers.UUIDField(help_text="Public ID del curso.")
    is_required = serializers.BooleanField(required=False, default=True)


class CurriculumPlanUpdateSerializer(serializers.Serializer):
    is_required = serializers.BooleanField(required=False)


# --------------------------------------------------------------------------- #
# teaching assignments
# --------------------------------------------------------------------------- #


class TeachingAssignmentSerializer(serializers.ModelSerializer):
    academic_cycle_id = serializers.UUIDField(source="academic_cycle.public_id", read_only=True)
    section_id = serializers.UUIDField(source="section.public_id", read_only=True)
    subject_id = serializers.UUIDField(source="subject.public_id", read_only=True)
    teacher_id = serializers.UUIDField(source="teacher.teacher_profile.public_id", read_only=True)

    class Meta:
        model = TeachingAssignment
        fields = [
            "public_id",
            "academic_cycle_id",
            "section_id",
            "subject_id",
            "teacher_id",
            "starts_on",
            "ends_on",
        ]


class TeachingAssignmentCreateSerializer(serializers.Serializer):
    academic_cycle_id = serializers.UUIDField(help_text="Public ID del ciclo escolar.")
    section_id = serializers.UUIDField(help_text="Public ID de la seccion.")
    subject_id = serializers.UUIDField(help_text="Public ID del curso.")
    teacher_id = serializers.UUIDField(help_text="Public ID del perfil Teacher activo.")
    starts_on = serializers.DateField(
        required=False,
        help_text="Fecha de inicio dentro del ciclo. Por defecto, inicia en la fecha del ciclo.",
    )


class TeachingAssignmentReassignSerializer(serializers.Serializer):
    teacher_id = serializers.UUIDField(help_text="Public ID del nuevo perfil Teacher activo.")
    ends_on = serializers.DateField(
        help_text="Ultimo dia inclusivo del docente vigente; el nuevo inicia al dia siguiente."
    )


# --------------------------------------------------------------------------- #
# historical cycle detail (RF-CIC-006)
# --------------------------------------------------------------------------- #


class HistoricalSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["public_id", "name", "capacity", "is_active"]


class HistoricalGradeOfferingSerializer(serializers.ModelSerializer):
    grade = GradeRefSerializer(read_only=True)
    shift = ShiftRefSerializer(read_only=True)
    campus = CampusRefSerializer(read_only=True)
    sections = HistoricalSectionSerializer(many=True, read_only=True)

    class Meta:
        model = GradeOffering
        fields = ["public_id", "grade", "shift", "campus", "sections", "is_active"]


class HistoricalCurriculumPlanSerializer(serializers.ModelSerializer):
    grade = GradeRefSerializer(read_only=True)
    subject = SubjectRefSerializer(read_only=True)

    class Meta:
        model = CurriculumPlan
        fields = ["public_id", "grade", "subject", "is_required", "is_active"]


class HistoricalEnrolmentSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField(source="_enrolment_total")
    active = serializers.IntegerField(source="_enrolment_active")
    withdrawn = serializers.IntegerField(source="_enrolment_withdrawn")
    completed = serializers.IntegerField(source="_enrolment_completed")
    cancelled = serializers.IntegerField(source="_enrolment_cancelled")


class HistoricalAcademicCycleSerializer(AcademicCycleSerializer):
    grade_offerings = HistoricalGradeOfferingSerializer(many=True, read_only=True)
    curriculum_plans = HistoricalCurriculumPlanSerializer(many=True, read_only=True)
    teaching_assignments = TeachingAssignmentSerializer(many=True, read_only=True)
    enrolments = HistoricalEnrolmentSummarySerializer(source="*", read_only=True)

    class Meta(AcademicCycleSerializer.Meta):
        fields = [
            *AcademicCycleSerializer.Meta.fields,
            "grade_offerings",
            "curriculum_plans",
            "teaching_assignments",
            "enrolments",
        ]
