from rest_framework import serializers

from apps.enrolments.models import Enrolment


class EnrolmentSerializer(serializers.ModelSerializer):
    student_code = serializers.CharField(source="student.student_code", read_only=True)
    student_name = serializers.SerializerMethodField()
    cycle_name = serializers.CharField(source="academic_cycle.name", read_only=True)
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)

    class Meta:
        model = Enrolment
        fields = [
            "public_id",
            "student_code",
            "student_name",
            "cycle_name",
            "grade_name",
            "section_name",
            "effective_on",
            "ends_on",
            "status",
        ]
        read_only_fields = ["public_id", "status"]

    def get_student_name(self, obj):
        person = obj.student.person
        return f"{person.first_name} {person.last_name}"


class EnrolmentCreateSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(help_text="Public ID of the student.")
    cycle_id = serializers.UUIDField(help_text="Public ID of the academic cycle.")
    grade_id = serializers.UUIDField(help_text="Public ID of the grade.")
    section_id = serializers.UUIDField(help_text="Public ID of the section.")
    effective_on = serializers.DateField(required=False)


class ReenrolSerializer(serializers.Serializer):
    new_cycle_id = serializers.UUIDField(help_text="Public ID of the target cycle.")
    new_grade_id = serializers.UUIDField(help_text="Public ID of the target grade.")
    new_section_id = serializers.UUIDField(help_text="Public ID of the target section.")
    effective_on = serializers.DateField(required=False)


class WithdrawSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)
    effective_on = serializers.DateField(required=False)


class ChangeSectionSerializer(serializers.Serializer):
    new_section_id = serializers.UUIDField(help_text="Public ID of the new section.")
    effective_on = serializers.DateField(required=False)
