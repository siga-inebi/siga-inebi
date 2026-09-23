from rest_framework import serializers

from apps.common.models import TaskRun


class TaskRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskRun
        fields = [
            "public_id",
            "name",
            "status",
            "started_at",
            "finished_at",
            "duration_ms",
            "host",
            "process_id",
            "summary",
            "error_type",
            "error_message",
        ]


class TaskRunQuerySerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=TaskRun.Status.choices, required=False)


class TaskHealthSerializer(serializers.Serializer):
    name = serializers.CharField()
    total_runs = serializers.IntegerField()
    failed_runs = serializers.IntegerField()
    running_runs = serializers.IntegerField()
    last_started_at = serializers.DateTimeField(allow_null=True)
    last_finished_at = serializers.DateTimeField(allow_null=True)
    last_status = serializers.CharField(allow_blank=True)
    last_duration_ms = serializers.IntegerField(allow_null=True)
    last_error_message = serializers.CharField(allow_blank=True)


class BackupStackHealthSerializer(serializers.Serializer):
    stack = serializers.CharField()
    artifact = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField(allow_null=True)
    age_hours = serializers.FloatField(allow_null=True)
    size_bytes = serializers.IntegerField(allow_null=True)
    sha256 = serializers.CharField(allow_blank=True)
    rpo_hours = serializers.IntegerField()
    meets_rpo = serializers.BooleanField()
    backup_count = serializers.IntegerField()
