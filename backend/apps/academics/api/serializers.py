from rest_framework import serializers

from apps.academics.models import Campus, Shift

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
