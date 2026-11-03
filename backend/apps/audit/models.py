from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class AuditEventQuerySet(models.QuerySet):
    """
    ``QuerySet.delete()``/``update()`` run a direct SQL statement and never
    call the model's ``delete()``/``save()`` overrides below, so without this
    a bulk ``AuditEvent.objects.filter(...).delete()`` would silently erase
    audit history (RF-BIT-005: immutable "with independence of role").
    """

    def delete(self):
        raise RuntimeError("Audit events cannot be deleted.")

    def update(self, **kwargs):
        raise RuntimeError("Audit events cannot be modified.")


class AuditEvent(TimeStampedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        null=True,
        blank=True,
    )
    actor_label = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=100)
    resource = models.CharField(max_length=150)
    resource_identifier = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    context = models.JSONField(default=dict, blank=True)

    objects = AuditEventQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        # Consultas de la consola de bitacora (AU1) y del historial de una
        # cuenta (U5): por accion (exacta o prefijo) en el tiempo, por autor en
        # el tiempo y por recurso afectado. Sin estos indices cada consulta
        # recorria la tabla completa, que crece con cada inicio de sesion.
        indexes = [
            models.Index(fields=["action", "-created_at"], name="audit_action_recent_idx"),
            models.Index(fields=["actor", "-created_at"], name="audit_actor_recent_idx"),
            models.Index(
                fields=["resource", "resource_identifier", "-created_at"],
                name="audit_resource_recent_idx",
            ),
            models.Index(fields=["-created_at"], name="audit_recent_idx"),
            # `action__startswith` (filtro por prefijo) solo usa un btree con
            # esta clase de operadores en PostgreSQL.
            models.Index(
                fields=["action"],
                name="audit_action_prefix_idx",
                opclasses=["varchar_pattern_ops"],
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("Audit events cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Audit events cannot be deleted.")
