from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("attendance", "0010_capture_batch")]

    operations = [
        migrations.AddField(model_name="capturebatch", name="closed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="capturebatch", name="session_key", field=models.CharField(blank=True, default="", max_length=64)),
    ]
