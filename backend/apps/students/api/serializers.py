from rest_framework import serializers

from apps.people.api.serializers import PersonSerializer
from apps.students.models import EmergencyContact, Guardian, Student, StudentGuardianRelation
from apps.students.services import create_guardian, create_student, create_student_guardian_relation

# --------------------------------------------------------------------------- #
# compact references, used whenever a payload needs to name a parent record
# without dragging in a full nested representation.
# --------------------------------------------------------------------------- #


class StudentRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ["public_id", "student_code"]


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
    person = PersonSerializer()

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

    def create(self, validated_data):
        person_data = validated_data.pop("person")
        actor = getattr(self.context.get("request"), "user", None)
        return create_guardian(person_data=person_data, actor=actor)

    def update(self, instance, validated_data):
        # Nested person edits aren't supported yet — edit via /api/v1/people/<id>/.
        validated_data.pop("person", None)
        return super().update(instance, validated_data)


class StudentGuardianRelationSerializer(serializers.ModelSerializer):
    guardian_detail = GuardianSerializer(source="guardian", read_only=True)

    class Meta:
        model = StudentGuardianRelation
        fields = [
            "id",
            "student",
            "guardian",
            "guardian_detail",
            "relationship_label",
            "is_primary",
            "starts_at",
            "ends_at",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_primary",
            "ends_at",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        actor = getattr(self.context.get("request"), "user", None)
        return create_student_guardian_relation(actor=actor, **validated_data)


class StudentGuardianRelationEndSerializer(serializers.Serializer):
    replacement_relation = serializers.PrimaryKeyRelatedField(
        queryset=StudentGuardianRelation.objects.all(),
        required=False,
        allow_null=True,
    )


class EmergencyContactSerializer(serializers.ModelSerializer):
    """Never exposes the internal ``id``: only ``public_id``, like ``people``."""

    student = StudentRefSerializer(read_only=True)

    class Meta:
        model = EmergencyContact
        fields = [
            "public_id",
            "student",
            "name",
            "phone_number",
            "relationship_label",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["public_id", "is_active", "created_at", "updated_at"]


class EmergencyContactCreateSerializer(serializers.Serializer):
    """The student is resolved from the URL, not from the payload."""

    name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=30)
    relationship_label = serializers.CharField(max_length=100)


class EmergencyContactUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    phone_number = serializers.CharField(max_length=30, required=False)
    relationship_label = serializers.CharField(max_length=100, required=False)
