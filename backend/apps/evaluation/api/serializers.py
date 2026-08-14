"""
API serializers for evaluation domain.

Contracts for POST/PATCH operations. Validation happens here before calling services.
"""

from rest_framework import serializers

from apps.evaluation.models import (
    CaptureExceptionGrant,
    CycleEvaluationConfig,
    EvaluationGlobalConfig,
    EvaluationUnit,
)


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
            "recovery_starts_on",
            "recovery_ends_on",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "academic_cycle",
            "public_id",
            "recovery_starts_on",
            "recovery_ends_on",
            "created_at",
            "updated_at",
        ]

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


class RecoveryWindowSerializer(serializers.Serializer):
    """Contract for configuring a unit's recovery window (RF-EVC-003)."""

    recovery_starts_on = serializers.DateField()
    recovery_ends_on = serializers.DateField()

    def validate(self, data):
        if data["recovery_starts_on"] > data["recovery_ends_on"]:
            raise serializers.ValidationError(
                {"recovery_ends_on": "Recovery window end date must be >= start date."}
            )
        return data


class CaptureExceptionGrantSerializer(serializers.ModelSerializer):
    """Contract for granting an exceptional capture window (RF-EVC-004)."""

    public_id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CaptureExceptionGrant
        fields = [
            "public_id",
            "evaluation_unit",
            "subject",
            "teacher",
            "reason",
            "expires_at",
            "created_at",
        ]
        read_only_fields = ["public_id", "evaluation_unit", "created_at"]


class EvaluationGlobalConfigSerializer(serializers.ModelSerializer):
    """Contract for the institution-wide evaluation configuration (RF-EVC-005)."""

    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = EvaluationGlobalConfig
        fields = ["default_unit_count", "updated_at"]

    def validate_default_unit_count(self, value):
        if value <= 0:
            raise serializers.ValidationError("default_unit_count must be a positive integer.")
        return value


class CycleEvaluationConfigSerializer(serializers.ModelSerializer):
    """Contract for a cycle's evaluation configuration override (RF-EVC-005)."""

    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CycleEvaluationConfig
        fields = ["unit_count", "updated_at"]

    def validate_unit_count(self, value):
        if value <= 0:
            raise serializers.ValidationError("unit_count must be a positive integer.")
        return value
