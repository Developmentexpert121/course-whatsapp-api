from django.urls import path, include
from .views import (
    AssessmentAttempts,
    AutomationRuleViewSet,
    WhatsAppBroadcastView,
    WhatsAppWebhookView,
    WhatsAppUserView,
    WhatsAppUserListView,
    home,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"automations", AutomationRuleViewSet, basename="automationrule")


urlpatterns = [
    path("", home, name="home"),
    path("webhook", WhatsAppWebhookView.as_view(), name="whatsapp_webhook"),
    path("users-list", WhatsAppUserListView.as_view(), name="whatsapp_users_POST"),
    path("users", WhatsAppUserView.as_view(), name="whatsapp_users_POST"),
    path(
        "users/<str:whatsapp_id>/",
        WhatsAppUserView.as_view(),
        name="whatsapp_users_GET_PUT_DELETE",
    ),
    path(
        "assessments/<str:user_id>/",
        AssessmentAttempts.as_view(),
        name="whatsapp_users_GET_PUT_DELETE",
    ),
    path(
        "broadcast/",
        WhatsAppBroadcastView.as_view(),
        name="whatsapp-broadcast",
    ),
    path("", include(router.urls)),
]
