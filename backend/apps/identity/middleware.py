from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.audit.services import record_event
from apps.identity.services import effective_session_idle_timeout_minutes, refresh_session_activity


class SessionIdleTimeoutMiddleware:
    """Expire server sessions from role policy before a protected operation runs."""

    session_activity_key = "identity.session_last_activity_at"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            return self.get_response(request)

        now = timezone.now()
        timeout_minutes = effective_session_idle_timeout_minutes(user=user, when=now)
        serialized_activity = request.session.get(self.session_activity_key)
        last_activity = (
            parse_datetime(serialized_activity) if isinstance(serialized_activity, str) else None
        )
        if last_activity and now - last_activity >= timedelta(minutes=timeout_minutes):
            record_event(
                actor=user,
                action="identity.session.expired",
                resource="UserAccount",
                resource_identifier=str(user.pk),
                context={"timeout_minutes": timeout_minutes, "result": "success"},
            )
            request.session.flush()
            response = JsonResponse(
                {"error": {"detail": "La sesión expiró por inactividad."}},
                status=401,
            )
            response["Cache-Control"] = "no-store"
            response["X-SIGA-Session-Expired"] = "1"
            return response

        refresh_session_activity(request=request, user=user, now=now)
        return self.get_response(request)
