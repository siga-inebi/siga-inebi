from rest_framework import serializers

from apps.academics.models import (
    AcademicCycle,
    Campus,
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
from apps.people.models import Person

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
        help_text="Codigo corto, unico por institucion. Se normaliza a mayusculas.",
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


class LevelCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, help_text="Ej. Preprimaria, Primaria, Basico.")
    code = serializers.CharField(max_length=30, help_text="Codigo unico por institucion.")
    sequence = serializers.IntegerField(
        min_value=1, help_text="Orden pedagogico del nivel. Unico por institucion."
    )


class LevelUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    sequence = serializers.IntegerField(min_value=1, required=False)


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
    code = serializers.CharField(max_length=30, help_text="Codigo unico por institucion.")
    sequence = serializers.IntegerField(min_value=1, help_text="Orden del grado dentro del nivel.")


class GradeUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    sequence = serializers.IntegerField(min_value=1, required=False)


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
# academic cycles ("ciclos escolares")
# --------------------------------------------------------------------------- #


class CycleRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicCycle
        fields = ["public_id", "name", "status"]


class TeacherRefSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ["public_id", "full_name"]

    def get_full_name(self, person) -> str:
        return f"{person.first_name} {person.last_name}".strip()


class AcademicCycleSerializer(serializers.ModelSerializer):
    """Every queryset that feeds this serializer annotates ``_offering_count``."""

    offering_count = serializers.IntegerField(source="_offering_count", read_only=True)

    class Meta:
        model = AcademicCycle
        fields = [
            "public_id",
            "name",
            "starts_on",
            "ends_on",
            "status",
            "is_active",
            "offering_count",
        ]


class AcademicCycleCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, help_text="Ej. Ciclo 2026.")
    starts_on = serializers.DateField(help_text="Primer dia del ciclo.")
    ends_on = serializers.DateField(help_text="Ultimo dia del ciclo, posterior al inicio.")


class AcademicCycleUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    starts_on = serializers.DateField(required=False)
    ends_on = serializers.DateField(required=False)


class AcademicCycleStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=AcademicCycle.CycleStatus.choices,
        help_text="Solo avanza: draft -> active -> closed.",
    )


# --------------------------------------------------------------------------- #
# grade offerings ("oferta de grados")
# --------------------------------------------------------------------------- #


class GradeOfferingSerializer(serializers.ModelSerializer):
    """Querysets annotate ``_section_count`` and ``_enrolment_count``."""

    academic_cycle = CycleRefSerializer(read_only=True)
    grade = GradeRefSerializer(read_only=True)
    shift = ShiftRefSerializer(read_only=True)
    campus = CampusRefSerializer(read_only=True)
    section_count = serializers.IntegerField(source="_section_count", read_only=True)
    enrolment_count = serializers.IntegerField(source="_enrolment_count", read_only=True)

    class Meta:
        model = GradeOffering
        fields = [
            "public_id",
            "academic_cycle",
            "grade",
            "shift",
            "campus",
            "is_active",
            "section_count",
            "enrolment_count",
        ]


class GradeOfferingCreateSerializer(serializers.Serializer):
    grade_id = serializers.UUIDField(help_text="Public ID del grado que se oferta.")
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada que lo atiende.")


class GradeOfferingRefSerializer(serializers.ModelSerializer):
    """Compact offering, used to place a section without repeating the counts."""

    academic_cycle = CycleRefSerializer(read_only=True)
    grade = GradeRefSerializer(read_only=True)
    shift = ShiftRefSerializer(read_only=True)

    class Meta:
        model = GradeOffering
        fields = ["public_id", "academic_cycle", "grade", "shift"]


# --------------------------------------------------------------------------- #
# sections ("secciones")
# --------------------------------------------------------------------------- #


class SectionSerializer(serializers.ModelSerializer):
    """
    Querysets annotate ``_active_enrolments`` and ``_assignment_count``.
    ``available_seats`` is ``null`` when the section declares no cap.
    """

    offering = GradeOfferingRefSerializer(read_only=True)
    enrolment_count = serializers.IntegerField(source="_active_enrolments", read_only=True)
    assignment_count = serializers.IntegerField(source="_assignment_count", read_only=True)
    available_seats = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Section
        fields = [
            "public_id",
            "name",
            "capacity",
            "is_active",
            "offering",
            "enrolment_count",
            "available_seats",
            "assignment_count",
        ]


class SectionCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50, help_text="Ej. A, B. Se normaliza a mayusculas.")
    capacity = serializers.IntegerField(
        min_value=0, required=False, default=0, help_text="0 significa sin cupo declarado."
    )


class SectionUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50, required=False)
    capacity = serializers.IntegerField(min_value=0, required=False)


# --------------------------------------------------------------------------- #
# curriculum plan ("plan de estudios del ciclo")
# --------------------------------------------------------------------------- #


class CurriculumPlanSerializer(serializers.ModelSerializer):
    academic_cycle = CycleRefSerializer(read_only=True)
    grade = GradeRefSerializer(read_only=True)
    subject = SubjectRefSerializer(read_only=True)

    class Meta:
        model = CurriculumPlan
        fields = ["public_id", "academic_cycle", "grade", "subject", "is_required"]


class CurriculumPlanCreateSerializer(serializers.Serializer):
    grade_id = serializers.UUIDField(help_text="Public ID del grado.")
    subject_id = serializers.UUIDField(help_text="Public ID del curso que se imparte.")
    is_required = serializers.BooleanField(required=False, default=True)


class CurriculumPlanUpdateSerializer(serializers.Serializer):
    is_required = serializers.BooleanField()


# --------------------------------------------------------------------------- #
# teaching assignments ("asignacion de docentes")
# --------------------------------------------------------------------------- #


class TeachingAssignmentSerializer(serializers.ModelSerializer):
    academic_cycle = CycleRefSerializer(read_only=True)
    subject = SubjectRefSerializer(read_only=True)
    teacher = TeacherRefSerializer(read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = TeachingAssignment
        fields = [
            "public_id",
            "academic_cycle",
            "subject",
            "teacher",
            "starts_on",
            "ends_on",
            "is_open",
        ]


class TeachingAssignmentCreateSerializer(serializers.Serializer):
    subject_id = serializers.UUIDField(help_text="Curso, que debe estar en el plan del grado.")
    teacher_id = serializers.UUIDField(help_text="Public ID de la persona docente.")
    starts_on = serializers.DateField(required=False, help_text="Por defecto, hoy.")


class TeachingAssignmentEndSerializer(serializers.Serializer):
    ends_on = serializers.DateField(required=False, help_text="Por defecto, hoy.")
