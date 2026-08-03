from rest_framework import serializers

from apps.students.models import Guardian, Student, StudentGuardianRelation


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            "id",
            "person",
            "student_code",
            "status",
            "photo_path",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]


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
