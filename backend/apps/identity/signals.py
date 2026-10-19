"""Conexion entre la autenticacion de Django y el registro de sesiones (riesgo A)."""

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from apps.identity.services import start_user_session


@receiver(user_logged_in, dispatch_uid="identity.start_user_session")
def register_user_session(sender, request, user, **kwargs):
    if request is not None:
        start_user_session(request=request, user=user)
