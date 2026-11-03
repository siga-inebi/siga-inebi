from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("academics", "0016_classroom_service_status")]

    operations = [
        migrations.AddField(
            model_name="grade",
            name="presentation_label",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
    ]
