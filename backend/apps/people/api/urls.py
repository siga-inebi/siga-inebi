from django.urls import path

from apps.people.api.views import PersonDetailView, PersonListCreateView

urlpatterns = [
    path("", PersonListCreateView.as_view(), name="person-list"),
    path("<int:pk>/", PersonDetailView.as_view(), name="person-detail"),
]
