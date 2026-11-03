from rest_framework import serializers

from apps.people.api.serializers import PersonSerializer, validate_institutional_person
from apps.teachers import queries
from apps.teachers.models import Teacher
from apps.teachers.services import create_teacher


class TeacherPositionSerializer(serializers.Serializer):
    value = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)


class TeacherListQuerySerializer(serializers.Serializer):
    include_inactive = serializers.BooleanField(default=False)
    position = serializers.ChoiceField(choices=Teacher.Position.choices, required=False)


class SuggestedEmployeeCodeSerializer(serializers.Serializer):
    """Siguiente codigo de empleado libre, para prellenar el formulario."""

    employee_code = serializers.CharField()


class TeacherSerializer(serializers.ModelSerializer):
    person = PersonSerializer(required=False)
    person_public_id = serializers.UUIDField(write_only=True, required=False)
    actions = serializers.SerializerMethodField()

    def get_actions(self, instance) -> dict[str, bool]:
        return queries.teacher_actions(
            teacher=instance, permissions=self.context.get("teacher_action_permissions", {})
        )

    class Meta:
        model = Teacher
        fields = [
            "id",
            "public_id",
            "person",
            "person_public_id",
            "employee_code",
            "specialty",
            "position",
            "appointment_date",
            "photo",
            "is_active",
            "created_at",
            "updated_at",
            "actions",
        ]
        read_only_fields = ["id", "public_id", "is_active", "created_at", "updated_at"]
        extra_kwargs = {
            # Opcional al crear: el servicio genera el siguiente de la serie
            # ("DOC-007"). Ver ``apps.teachers.services.create_teacher``.
            "employee_code": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        person_data = validated_data.pop("person", None)
        person_public_id = validated_data.pop("person_public_id", None)
        actor = getattr(self.context.get("request"), "user", None)
        return create_teacher(
            person_data=person_data,
            person_public_id=person_public_id,
            employee_code=validated_data.get("employee_code"),
            specialty=validated_data["specialty"],
            position=validated_data["position"],
            appointment_date=validated_data.get("appointment_date"),
            actor=actor,
        )

    def validate(self, attrs):
        if self.instance is None:
            if not attrs.get("person") and not attrs.get("person_public_id"):
                raise serializers.ValidationError("Indique person o person_public_id.")
            if not attrs.get("person_public_id"):
                validate_institutional_person(attrs.get("person"))
        elif "person_public_id" in attrs:
            raise serializers.ValidationError("person_public_id solo se acepta al crear.")
        return attrs

    def update(self, instance, validated_data):
        # Nested person edits aren't supported here either — edit via /api/v1/people/<id>/.
        validated_data.pop("person", None)
        return super().update(instance, validated_data)
