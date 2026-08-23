from django.contrib import admin

from apps.enrolments.models import Enrolment, StudentMovement

admin.site.register(Enrolment)
admin.site.register(StudentMovement)
