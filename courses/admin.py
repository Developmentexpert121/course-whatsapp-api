from django.contrib import admin
from .models import (
    Course,
    CourseDescription,
    CourseDescriptionImage,
    Module,
    Assessment,
    AssessmentQuestion,
    Topic,
    TopicParagraph,
)

# Register your models here.
admin.site.register(Course)
admin.site.register(Module)
admin.site.register(Assessment)
admin.site.register(AssessmentQuestion)
admin.site.register(Topic)
admin.site.register(TopicParagraph)
admin.site.register(CourseDescription)
admin.site.register(CourseDescriptionImage)
