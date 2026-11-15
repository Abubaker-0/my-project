"""Django admin registration for classes."""

from django.contrib import admin

from apps.classes.models import ClassSchedule, Classroom, CourseClass

admin.site.register(Classroom)
admin.site.register(CourseClass)
admin.site.register(ClassSchedule)
