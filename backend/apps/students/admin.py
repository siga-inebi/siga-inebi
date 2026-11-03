from django.contrib import admin

from apps.students.models import EmergencyContact, Guardian, Student, StudentGuardianRelation

admin.site.register(Student)
admin.site.register(Guardian)
admin.site.register(StudentGuardianRelation)
admin.site.register(EmergencyContact)
