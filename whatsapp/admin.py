from django.contrib import admin
from .models import (
    ModuleDeliveryProgress,
    WhatsappUser,
    UserEnrollment,
    UserAssessmentAttempt,
    UserQuestionResponse,
)

# Register your models here.
admin.site.register(WhatsappUser)
admin.site.register(UserEnrollment)
admin.site.register(ModuleDeliveryProgress)
admin.site.register(UserAssessmentAttempt)
admin.site.register(UserQuestionResponse)
