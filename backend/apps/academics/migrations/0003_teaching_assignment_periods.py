from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0002_academic_catalogue"),
    ]

    operations = [
        BtreeGistExtension(),
        migrations.AddConstraint(
            model_name="teachingassignment",
            constraint=models.CheckConstraint(
                check=models.Q(("ends_on__isnull", True), ("starts_on__lte", models.F("ends_on")), _connector="OR"),
                name="teaching_assignment_valid_dates",
            ),
        ),
        migrations.AddConstraint(
            model_name="teachingassignment",
            constraint=ExclusionConstraint(
                expressions=[
                    ("academic_cycle", RangeOperators.EQUAL),
                    ("section", RangeOperators.EQUAL),
                    ("subject", RangeOperators.EQUAL),
                    (
                        models.Func(
                            models.F("starts_on"),
                            models.F("ends_on"),
                            models.Value("[]"),
                            function="DATERANGE",
                            output_field=DateRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                name="teaching_assignment_no_overlapping_period",
            ),
        ),
    ]
