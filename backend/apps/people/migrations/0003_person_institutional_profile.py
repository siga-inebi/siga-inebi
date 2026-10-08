from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("people", "0002_person_birth_date")]

    operations = [
        migrations.AddField(model_name="person", name="cui", field=models.CharField(blank=True, max_length=13, null=True, unique=True)),
        migrations.AddField(model_name="person", name="sex", field=models.CharField(choices=[("female", "Femenino"), ("male", "Masculino"), ("not_specified", "No especificado")], default="not_specified", max_length=20)),
        migrations.AddField(model_name="person", name="nationality", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="person", name="address", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="person", name="department", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="person", name="municipality", field=models.CharField(blank=True, max_length=100)),
    ]
