"""
Academic evaluation domain.

Manages evaluation units (trimesters, bimesters) within academic cycles,
capture windows, recovery periods, and exceptional authorization breaches.

No business logic lives in views or serializers (AGENTS.md #8).
Authorization checked at view layer; domain constraints enforced in services.
"""

default_app_config = "apps.evaluation.apps.EvaluationConfig"
