import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("academics", "0010_classroom")]

    operations = [
        migrations.AddField(
            model_name="classsession",
            name="classroom",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="class_sessions", to="academics.classroom"),
        )
    ]
