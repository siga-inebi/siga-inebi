from django.urls import path

from .views import (
    CampusDetailView,
    CampusListCreateView,
    CampusShiftListCreateView,
    ShiftDetailView,
)

urlpatterns = [
    # institutional structure: sedes y jornadas
    path("campuses/", CampusListCreateView.as_view(), name="campus-list-create"),
    path("campuses/<uuid:public_id>/", CampusDetailView.as_view(), name="campus-detail"),
    path(
        "campuses/<uuid:public_id>/shifts/",
        CampusShiftListCreateView.as_view(),
        name="campus-shift-list-create",
    ),
    path("shifts/<uuid:public_id>/", ShiftDetailView.as_view(), name="shift-detail"),
]
