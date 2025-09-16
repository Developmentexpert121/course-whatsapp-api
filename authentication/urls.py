from django.urls import path
from .views import AdminView, ResendCredentials, home, LoginView

urlpatterns = [
    path("", home, name="home"),
    path("login", LoginView.as_view(), name="login"),
    path("admin", AdminView.as_view(), name="admin"),
    path("resend_credentials", ResendCredentials.as_view(), name="resend credentials"),
]
