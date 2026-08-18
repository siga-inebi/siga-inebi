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

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("Audit events cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Audit events cannot be deleted.")
