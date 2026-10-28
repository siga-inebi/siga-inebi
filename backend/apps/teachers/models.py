from django.db import models

from apps.common.models import TimeStampedModel
from apps.common.uploads import profile_photo_upload_path


def teacher_photo_upload_to(instance, filename):
    """Name the photo by its purpose and stable institutional owner code."""
    return profile_photo_upload_path(
        directory="teacher_photos",
        subject="docente",
        owner_identifier=instance.employee_code or instance.public_id,
        filename=filename,
    )


class Teacher(TimeStampedModel):
    class Position(models.TextChoices):
        DOCENTE_TITULADO = "Docente Titulado", "Docente Titulado"
        DOCENTE_INTERINO = "Docente Interino", "Docente Interino"
        ORIENTADOR = "Orientador/a", "Orientador/a"
        ADMINISTRATIVO = "Administrativo", "Administrativo"

    person = models.OneToOneField(
        "people.Person",
        on_delete=models.PROTECT,
        related_name="teacher_profile",
    )
    employee_code = models.CharField(max_length=50, unique=True)
    specialty = models.CharField(max_length=150)
    position = models.CharField(max_length=20, choices=Position.choices)
    appointment_date = models.DateField(null=True, blank=True)
    photo = models.FileField(upload_to=teacher_photo_upload_to, blank=True)

    class Meta:
        # Orden explicito: sin el, paginar es un sorteo. PostgreSQL no garantiza
        # el mismo orden entre dos consultas con LIMIT/OFFSET sobre un queryset
        # sin ordenar, asi que recorrer las paginas devolvia filas repetidas y
        # omitia otras (DRF lo avisa con UnorderedObjectListWarning).
        ordering = ["employee_code"]

    def __str__(self):
        return self.employee_code
