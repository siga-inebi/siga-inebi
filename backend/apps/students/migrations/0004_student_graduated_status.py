from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("students", "0003_studentguardianrelation_current_primary"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="status",
            field=models.CharField(
                choices=[
                    ("pre_enrolled", "Pre-enrolled"),
                    ("active", "Active"),
                    ("inactive", "Inactive"),
                    ("withdrawn", "Withdrawn"),
                    ("graduated", "Graduated"),
                ],
                default="pre_enrolled",
                max_length=20,
            ),
        ),
    ]
