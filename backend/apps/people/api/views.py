from rest_framework import generics

from apps.people.api.serializers import PersonSerializer
from apps.people.models import Person
from apps.people.services import create_person, deactivate_person, update_person


class PersonListCreateView(generics.ListCreateAPIView):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer

    def perform_create(self, serializer):
        serializer.instance = create_person(actor=self.request.user, **serializer.validated_data)


class PersonDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    lookup_field = "public_id"

    def perform_update(self, serializer):
        update_person(
            person=serializer.instance, actor=self.request.user, **serializer.validated_data
        )

    def perform_destroy(self, instance):
        deactivate_person(person=instance, actor=self.request.user)
