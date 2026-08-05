from rest_framework import serializers

from apps.people.api.serializers import PersonSerializer
from apps.students.models import EmergencyContact, Guardian, Student, StudentGuardianRelation
from apps.students.services import create_student


class StudentSerializer(serializers.ModelSerializer):
    person = PersonSerializer()

    class Meta:
        model = Student
        fields = [
            "id",
            "person",
            "student_code",
            "status",
            "photo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]

    def create(self, validated_data):
        person_data = validated_data.pop("person")
        actor = getattr(self.context.get("request"), "user", None)
        return create_student(
            person_data=person_data,
            student_code=validated_data["student_code"],
            status=validated_data.get("status"),
            actor=actor,
        )

    def update(self, instance, validated_data):
        # Nested person edits aren't supported yet — edit via /api/v1/people/<id>/.
        validated_data.pop("person", None)
        return super().update(instance, validated_data)


class GuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = [
            "id",
            "person",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]


class StudentGuardianRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentGuardianRelation
        fields = [
            "id",
            "student",
            "guardian",
            "relationship_label",
            "is_primary",
            "starts_at",
            "ends_at",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "ends_at", "is_active", "created_at", "updated_at"]


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = [
            "id",
            "student",
            "name",
            "phone_number",
            "relationship_label",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]
