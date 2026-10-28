from django.db import migrations, models

import apps.teachers.models


class Migration(migrations.Migration):
    dependencies = [
        ("teachers", "0002_alter_teacher_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="teacher",
            name="photo",
            field=models.FileField(
                blank=True,
                upload_to=apps.teachers.models.teacher_photo_upload_to,
            ),
        ),
    ]
