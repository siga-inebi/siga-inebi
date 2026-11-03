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
        ('people', '0001_initial'),
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
                ('capture_starts_on', models.DateField(help_text='Date when grade capture window opens (independent of evaluation dates).')),
                ('capture_ends_on', models.DateField(help_text='Date when grade capture window closes; after this, no capture is allowed.')),
                ('recovery_starts_on', models.DateField(blank=True, help_text='Date when the recovery window opens. Optional; unset until configured.', null=True)),
                ('recovery_ends_on', models.DateField(blank=True, help_text='Date when the recovery window closes. Optional; unset until configured.', null=True)),
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
            constraint=models.CheckConstraint(condition=models.Q(('capture_starts_on__lte', models.F('capture_ends_on'))), name='evaluation_unit_valid_capture_dates'),
        ),
        migrations.AddConstraint(
            model_name='evaluationunit',
            constraint=models.CheckConstraint(condition=(models.Q(('recovery_ends_on__isnull', True), ('recovery_starts_on__isnull', True)) | models.Q(('recovery_ends_on__isnull', False), ('recovery_starts_on__isnull', False), ('recovery_starts_on__lte', models.F('recovery_ends_on')))), name='evaluation_unit_valid_recovery_dates'),
        ),
        migrations.AddConstraint(
            model_name='evaluationunit',
            constraint=ExclusionConstraint(expressions=[('academic_cycle', RangeOperators.EQUAL), (models.Func(models.F('starts_on'), models.F('ends_on'), models.Value('[]'), function='DATERANGE', output_field=DateRangeField()), RangeOperators.OVERLAPS)], name='evaluation_unit_no_overlapping_dates'),
        ),
        migrations.CreateModel(
            name='CaptureExceptionGrant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('reason', models.TextField(help_text='Justification required to grant the exception.')),
                ('expires_at', models.DateTimeField(help_text='Moment the grant lapses automatically.')),
                ('evaluation_unit', models.ForeignKey(help_text='Unit this exceptional capture grant applies to.', on_delete=django.db.models.deletion.CASCADE, related_name='capture_exceptions', to='evaluation.evaluationunit')),
                ('subject', models.ForeignKey(help_text='Subarea the grant is scoped to.', on_delete=django.db.models.deletion.PROTECT, related_name='capture_exceptions', to='academics.subject')),
                ('teacher', models.ForeignKey(help_text='Teacher authorized to capture grades during the grant.', on_delete=django.db.models.deletion.PROTECT, related_name='capture_exceptions', to='people.person')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='EvaluationGlobalConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('singleton_key', models.BooleanField(default=True, editable=False, unique=True)),
                ('default_unit_count', models.PositiveSmallIntegerField(default=4, help_text='Default number of evaluation units suggested for new cycles.')),
            ],
        ),
        migrations.AddConstraint(
            model_name='evaluationglobalconfig',
            constraint=models.CheckConstraint(condition=models.Q(('default_unit_count__gt', 0)), name='evaluation_global_config_positive_unit_count'),
        ),
        migrations.CreateModel(
            name='CycleEvaluationConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('unit_count', models.PositiveSmallIntegerField(blank=True, help_text='Cycle-specific unit count override. Null inherits the global default.', null=True)),
                ('academic_cycle', models.OneToOneField(help_text='Cycle this configuration override belongs to.', on_delete=django.db.models.deletion.CASCADE, related_name='evaluation_config', to='academics.academiccycle')),
            ],
        ),
        migrations.AddConstraint(
            model_name='cycleevaluationconfig',
            constraint=models.CheckConstraint(condition=(models.Q(('unit_count__isnull', True)) | models.Q(('unit_count__gt', 0))), name='cycle_evaluation_config_positive_unit_count'),
        ),
    ]
