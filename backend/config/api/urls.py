from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.api.views import DatabaseHealthView, HealthView, LoginView, LogoutView, MeView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("health/database/", DatabaseHealthView.as_view(), name="health-database"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
]
