from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.api.views import (
    DatabaseHealthView,
    HealthView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("health/database/", DatabaseHealthView.as_view(), name="health-database"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/password/change/", PasswordChangeView.as_view(), name="auth-password-change"),
    path("audit/", include("apps.audit.api.urls")),
    path("identity/", include("apps.identity.api.urls")),
    path("people/", include("apps.people.api.urls")),
    path("students/", include("apps.students.api.urls")),
    path("teachers/", include("apps.teachers.api.urls")),
    path("academics/", include("apps.academics.api.urls")),
    path("attendance/", include("apps.attendance.api.urls")),
    path("reporting/", include("apps.reporting.api.urls")),
    path("documents/", include("apps.documents.api.urls")),
    path("enrolments/", include("apps.enrolments.api.urls")),
]
