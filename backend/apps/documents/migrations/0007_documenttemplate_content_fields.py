from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0006_alter_documentdownloadtoken_expires_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="documenttemplate",
            name="content",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="documenttemplateversion",
            name="content",
            field=models.TextField(blank=True, default=""),
        ),
    ]
