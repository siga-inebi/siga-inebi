import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0009_documentbatchrun'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentVerificationCode',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('code', models.CharField(max_length=64, unique=True)),
                ('document_type', models.CharField(blank=True, max_length=100)),
                ('issued_at', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
