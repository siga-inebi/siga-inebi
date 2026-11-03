from django.db import models

from apps.common.models import TimeStampedModel


class Person(TimeStampedModel):
    class Sex(models.TextChoices):
        FEMALE = "female", "Femenino"
        MALE = "male", "Masculino"
        NOT_SPECIFIED = "not_specified", "No especificado"

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    cui = models.CharField(max_length=13, unique=True, null=True, blank=True)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    institutional_identifier = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=20, choices=Sex.choices, default=Sex.NOT_SPECIFIED)
    nationality = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=100, blank=True)
    municipality = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()
