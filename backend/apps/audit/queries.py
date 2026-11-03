"""Read-side queries over the audit trail that other domains display."""

from django.db.models import Q

from apps.audit.models import AuditEvent

ACCOUNT_ACTIVITY_LIMIT = 20


def account_activity(*, account_pk, limit=ACCOUNT_ACTIVITY_LIMIT):
    """
    U5: historial reciente de accesos y operaciones sobre una cuenta.

    Junta lo que la propia cuenta hizo con su sesion (inicios, cierres,
    vencimientos) y lo que se hizo sobre ella (desactivacion, reactivacion,
    desbloqueo, intentos fallidos, restablecimientos). Los intentos fallidos no
    tienen actor, por eso tambien se busca por ``resource_identifier``.
    """
    return AuditEvent.objects.filter(
        Q(resource="UserAccount", resource_identifier=str(account_pk))
        | Q(actor_id=account_pk, action__startswith="identity.session")
        | Q(actor_id=account_pk, action__startswith="identity.login")
    ).order_by("-created_at")[:limit]
