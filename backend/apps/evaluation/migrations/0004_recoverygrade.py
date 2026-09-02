import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_academic_cycle_foundation'),
        ('enrolments', '0003_enrolmentdocumentrequirement'),
        ('evaluation', '0003_grade_grade_value_within_scale'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecoveryGrade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('value', models.PositiveSmallIntegerField(help_text='Result of the recovery evaluation, on the same 0-100 scale.')),
                ('original_final_grade', models.PositiveSmallIntegerField(help_text='Snapshot of the rounded final grade before the recovery, kept for the boleta.')),
                ('enrolment', models.ForeignKey(help_text='Ties the recovery grade to the student, the section and the cycle.', on_delete=django.db.models.deletion.PROTECT, related_name='recovery_grades', to='enrolments.enrolment')),
                ('subject', models.ForeignKey(help_text='Failed subarea the recovery grade applies to.', on_delete=django.db.models.deletion.PROTECT, related_name='recovery_grades', to='academics.subject')),
            ],
            options={
                'ordering': ['enrolment', 'subject'],
                'constraints': [
                    models.UniqueConstraint(fields=('enrolment', 'subject'), name='unique_recovery_grade_per_enrolment_subject'),
                    models.CheckConstraint(condition=models.Q(('value__gte', 0), ('value__lte', 100)), name='recovery_grade_value_within_scale'),
                ],
            },
        ),
    ]
