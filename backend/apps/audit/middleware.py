from threading import local

_state = local()


def get_audit_context():
    return getattr(_state, "context", {})


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _state.context = {
            "ip_address": request.META.get("REMOTE_ADDR", ""),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "path": request.path,
        }
        return self.get_response(request)
