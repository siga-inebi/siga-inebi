from django.db import migrations, models

import apps.students.models


class Migration(migrations.Migration):
    dependencies = [
        ("students", "0008_seed_guardian_deactivate_permission"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="photo",
            field=models.FileField(
                blank=True,
                upload_to=apps.students.models.student_photo_upload_to,
            ),
        ),
    ]
