from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("enrolments", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="enrolment",
            constraint=models.CheckConstraint(
                check=Q(ends_on__isnull=True) | Q(effective_on__lte=F("ends_on")),
                name="enrolment_valid_effective_dates",
            ),
        ),
    ]
