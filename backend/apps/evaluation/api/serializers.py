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
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["academic_cycle", "public_id", "created_at", "updated_at"]

    def validate(self, data):
        """Validate date range before passing to service."""
        if data["starts_on"] > data["ends_on"]:
            raise serializers.ValidationError(
                {"ends_on": "End date must be >= start date."}
            )
        return data
