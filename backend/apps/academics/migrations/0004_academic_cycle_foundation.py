from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import migrations, models


def populate_cycle_year(apps, schema_editor):
    AcademicCycle = apps.get_model("academics", "AcademicCycle")
    for cycle in AcademicCycle.objects.only("pk", "starts_on").iterator():
        AcademicCycle.objects.filter(pk=cycle.pk).update(year=cycle.starts_on.year)


class Migration(migrations.Migration):
    dependencies = [("academics", "0003_teaching_assignment_periods")]

    operations = [
        migrations.AddField(
            model_name="academiccycle",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="academiccycle",
            name="year",
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.RunPython(populate_cycle_year, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="academiccycle",
            name="year",
            field=models.PositiveSmallIntegerField(),
        ),
        migrations.AlterUniqueTogether(name="academiccycle", unique_together=set()),
        migrations.AlterModelOptions(
            name="academiccycle",
            options={"ordering": ["-year", "starts_on"]},
        ),
        migrations.AddConstraint(
            model_name="academiccycle",
            constraint=models.UniqueConstraint(
                fields=("institution", "name"),
                name="unique_cycle_name_per_institution",
            ),
        ),
        migrations.AddConstraint(
            model_name="academiccycle",
            constraint=models.UniqueConstraint(
                fields=("institution", "year"),
                name="unique_cycle_year_per_institution",
            ),
        ),
        migrations.AddConstraint(
            model_name="academiccycle",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="active"),
                fields=("institution",),
                name="unique_active_cycle_per_institution",
            ),
        ),
        migrations.AddConstraint(
            model_name="academiccycle",
            constraint=models.CheckConstraint(
                condition=models.Q(starts_on__lte=models.F("ends_on")),
                name="academic_cycle_valid_dates",
            ),
        ),
        migrations.AddConstraint(
            model_name="academiccycle",
            constraint=ExclusionConstraint(
                expressions=[
                    ("institution", RangeOperators.EQUAL),
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
                name="academic_cycle_no_overlapping_dates",
            ),
        ),
    ]
