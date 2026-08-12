# Generated migration for EvaluationUnit model

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('academics', '0004_academic_cycle_foundation'),
    ]

    operations = [
        migrations.CreateModel(
            name='EvaluationUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('number', models.PositiveSmallIntegerField(help_text='Order within the cycle: 1, 2, 3, 4, etc.')),
                ('name', models.CharField(help_text="Display name: 'Unit 1', 'First Trimester', etc.", max_length=100)),
                ('starts_on', models.DateField(help_text='First day of evaluation period.')),
                ('ends_on', models.DateField(help_text='Last day of evaluation period.')),
                ('status', models.CharField(choices=[('open', 'Open'), ('closed', 'Closed')], default='open', help_text='OPEN: accepts grade capture; CLOSED: no capture unless authorized breach.', max_length=20)),
                ('academic_cycle', models.ForeignKey(help_text='Cycle this evaluation unit belongs to.', on_delete=django.db.models.deletion.CASCADE, related_name='evaluation_units', to='academics.academiccycle')),
            ],
            options={
                'ordering': ['academic_cycle', 'number'],
            },
        ),
        migrations.AddConstraint(
            model_name='evaluationunit',
            constraint=models.UniqueConstraint(fields=['academic_cycle', 'number'], name='unique_unit_number_per_cycle'),
        ),
        migrations.AddConstraint(
            model_name='evaluationunit',
            constraint=models.CheckConstraint(condition=models.Q(('starts_on__lte', models.F('ends_on'))), name='evaluation_unit_valid_dates'),
        ),
        migrations.AddConstraint(
            model_name='evaluationunit',
            constraint=ExclusionConstraint(expressions=[('academic_cycle', RangeOperators.EQUAL), (models.Func(models.F('starts_on'), models.F('ends_on'), models.Value('[]'), function='DATERANGE', output_field=DateRangeField()), RangeOperators.OVERLAPS)], name='evaluation_unit_no_overlapping_dates'),
        ),
    ]
