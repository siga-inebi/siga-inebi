from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.academics.models import (
    AcademicCycle,
    Campus,
    Grade,
    GradeOffering,
    Level,
    LevelSubject,
    Section,
    Shift,
    Subject,
)

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
# sections
# --------------------------------------------------------------------------- #


class SectionSerializer(serializers.ModelSerializer):
    campus = CampusRefSerializer(read_only=True)
    shift = ShiftRefSerializer(read_only=True)
    level = LevelRefSerializer(read_only=True)
    grade = GradeRefSerializer(read_only=True)
    offering_id = serializers.UUIDField(source="offering.public_id", read_only=True)
    active_enrolment_count = serializers.IntegerField(read_only=True)
    available_seats = serializers.SerializerMethodField(
        help_text="Cupos libres. null cuando la seccion no declara cupo."
    )

    class Meta:
        model = Section
        fields = [
            "public_id",
            "name",
            "capacity",
            "is_active",
            "offering_id",
            "campus",
            "shift",
            "level",
            "grade",
            "active_enrolment_count",
            "available_seats",
        ]

    @extend_schema_field(OpenApiTypes.INT)
    def get_available_seats(self, obj):
        return obj.available_seats


class SectionCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50, help_text="Ej. A. Se normaliza a mayusculas.")
    capacity = serializers.IntegerField(
        min_value=0, help_text="Cupo declarado. 0 significa sin limite."
    )


class SectionUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50, required=False)
    capacity = serializers.IntegerField(min_value=0, required=False)


# --------------------------------------------------------------------------- #
# grade offerings
# --------------------------------------------------------------------------- #


class GradeOfferingSerializer(serializers.ModelSerializer):
    campus = CampusRefSerializer(read_only=True)
    shift = ShiftRefSerializer(read_only=True)
    level = LevelRefSerializer(read_only=True)
    grade = GradeRefSerializer(read_only=True)
    section_count = serializers.IntegerField(source="_section_count", read_only=True)

    class Meta:
        model = GradeOffering
        fields = ["public_id", "campus", "shift", "level", "grade", "section_count"]


class GradeOfferingCreateSerializer(serializers.Serializer):
    grade_id = serializers.UUIDField(help_text="Public ID del grado a ofertar.")
    shift_id = serializers.UUIDField(help_text="Public ID de la jornada, que define la sede.")


# --------------------------------------------------------------------------- #
# cycles
# --------------------------------------------------------------------------- #


class AcademicCycleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicCycle
        fields = ["public_id", "name", "starts_on", "ends_on", "status"]
        read_only_fields = ["public_id", "status"]


class AcademicCycleDetailSerializer(serializers.ModelSerializer):
    """
    Summary of a cycle. The sections themselves are not embedded: a cycle can
    hold hundreds of them, so they are fetched, paginated, through
    ``offerings/{id}/sections/``.
    """

    offering_count = serializers.IntegerField(source="_offering_count", read_only=True)
    section_count = serializers.IntegerField(source="_section_count", read_only=True)

    class Meta:
        model = AcademicCycle
        fields = [
            "public_id",
            "name",
            "starts_on",
            "ends_on",
            "status",
            "offering_count",
            "section_count",
        ]
        read_only_fields = ["public_id", "status"]


class AcademicCycleCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()

    def validate(self, data):
        if data["ends_on"] <= data["starts_on"]:
            raise serializers.ValidationError({"ends_on": "End date must be after start date."})
        return data
