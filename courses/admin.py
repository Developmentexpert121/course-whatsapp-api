from django.contrib import admin
from .models import Course, Module, Assessment, AssessmentQuestion

# Register your models here.
admin.site.register(Course)
admin.site.register(Module)
admin.site.register(Assessment)
admin.site.register(AssessmentQuestion)
