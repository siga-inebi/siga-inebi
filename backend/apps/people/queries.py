"""Read-side queries for institutional people."""

from apps.people.models import Person


def people():
    return Person.objects.all()
