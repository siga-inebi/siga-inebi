from rest_framework import serializers

from apps.people.api.serializers import PersonSerializer
from apps.teachers.models import Teacher
from apps.teachers.services import create_teacher


class TeacherSerializer(serializers.ModelSerializer):
    person = PersonSerializer()

    class Meta:
        model = Teacher
        fields = [
            "id",
            "public_id",
            "person",
            "employee_code",
            "specialty",
            "position",
            "appointment_date",
            "photo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "is_active", "created_at", "updated_at"]

    def create(self, validated_data):
        person_data = validated_data.pop("person")
        actor = getattr(self.context.get("request"), "user", None)
        return create_teacher(
            person_data=person_data,
            employee_code=validated_data["employee_code"],
            specialty=validated_data["specialty"],
            position=validated_data["position"],
            appointment_date=validated_data.get("appointment_date"),
            actor=actor,
        )

    def update(self, instance, validated_data):
        # Nested person edits aren't supported here either — edit via /api/v1/people/<id>/.
        validated_data.pop("person", None)
        return super().update(instance, validated_data)
