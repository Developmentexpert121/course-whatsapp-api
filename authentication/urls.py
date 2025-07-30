from django.urls import path
from .views import home, LoginView

urlpatterns = [
    path("", home, name="home"),
    path("login", LoginView.as_view(), name="login"),
]
