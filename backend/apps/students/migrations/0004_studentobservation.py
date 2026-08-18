import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("students", "0003_studentguardianrelation_current_primary"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("description", models.TextField()),
                ("observed_on", models.DateField(default=django.utils.timezone.localdate)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="student_observations", to=settings.AUTH_USER_MODEL)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="observations", to="students.student")),
            ],
            options={"ordering": ["-observed_on", "-created_at"]},
        ),
    ]
