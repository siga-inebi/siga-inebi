import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("academics", "0017_grade_presentation_label")]

    operations = [
        migrations.CreateModel(
            name="NonComputableDay",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("day", models.DateField()),
                ("reason", models.CharField(max_length=255)),
                ("academic_cycle", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="non_computable_days", to="academics.academiccycle")),
            ],
            options={"ordering": ["day"]},
        ),
        migrations.AddConstraint(
            model_name="noncomputableday",
            constraint=models.UniqueConstraint(fields=("academic_cycle", "day"), name="unique_non_computable_day_per_cycle"),
        ),
    ]
