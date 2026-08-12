"""
API serializers for evaluation domain.

Contracts for POST/PATCH operations. Validation happens here before calling services.
"""

from rest_framework import serializers

from apps.evaluation.models import EvaluationUnit


class EvaluationUnitSerializer(serializers.ModelSerializer):
    """Read and write evaluation units via REST API."""

    public_id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = EvaluationUnit
        fields = [
            "public_id",
            "academic_cycle",
            "number",
            "name",
            "starts_on",
            "ends_on",
            "capture_starts_on",
            "capture_ends_on",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["academic_cycle", "public_id", "created_at", "updated_at"]

    def validate(self, data):
        """Validate date ranges before passing to service."""
        if data["starts_on"] > data["ends_on"]:
            raise serializers.ValidationError(
                {"ends_on": "Evaluation end date must be >= start date."}
            )
        if data["capture_starts_on"] > data["capture_ends_on"]:
            raise serializers.ValidationError(
                {"capture_ends_on": "Capture window end date must be >= start date."}
            )
        return data
