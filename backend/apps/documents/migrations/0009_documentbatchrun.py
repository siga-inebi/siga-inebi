import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0008_documentdeliveryreceipt'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentBatchRun',
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
                ('client_batch_id', models.CharField(blank=True, default='', max_length=100)),
                ('document_type', models.CharField(max_length=100)),
                ('enrolment_count', models.PositiveIntegerField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddConstraint(
            model_name='documentbatchrun',
            constraint=models.UniqueConstraint(
                condition=models.Q(('client_batch_id', ''), _negated=True),
                fields=('client_batch_id',),
                name='unique_document_batch_run_client_batch_id',
            ),
        ),
    ]
