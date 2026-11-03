from django.db import migrations


class Migration(migrations.Migration):
    """
    Merge point of the expediente branches.

    It used to merge three leaves: ``0004_student_graduated_status``,
    ``0004_studenthealthnote`` and ``0004_studentobservation``. The last two were
    folded into ``0004_student_graduated_status`` (it creates both models), and
    deleting their files left this migration pointing at nodes that no longer
    exist — which is a graph that cannot even be loaded, so every management
    command and every test errored out.

    The node itself stays: it is already recorded in deployed databases and
    ``0006`` depends on it. Only the dangling parents are gone.
    """

    dependencies = [
        ("students", "0004_student_graduated_status"),
    ]

    operations = []
