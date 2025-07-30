from django.urls import path
from .views import WhatsAppWebhookView, WhatsAppUserView, WhatsAppUserListView, home

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
]
