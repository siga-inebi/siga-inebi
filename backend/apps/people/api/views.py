from rest_framework import generics

from apps.people.api.serializers import PersonSerializer
from apps.people.models import Person
from apps.people.services import deactivate_person


class PersonListCreateView(generics.ListCreateAPIView):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer


class PersonDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer

    def perform_destroy(self, instance):
        deactivate_person(person=instance, actor=self.request.user)
