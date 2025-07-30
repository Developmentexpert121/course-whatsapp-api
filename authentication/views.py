import secrets
from django.contrib.auth.hashers import check_password
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse  # Only for set_cookie
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User  # Replace with your actual User model path

# Create your views here.


def home(request):
    return HttpResponse("Welcome to the Authentication Home Page")


class LoginView(APIView):
    authentication_classes = []  # Disable auth for login
    permission_classes = []  # Allow any user to access

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = User.objects.filter(email=email).first()

        if user and password == user.password:
            refresh = RefreshToken.for_user(user)

            # Use JsonResponse only to set cookie
            response = Response(
                {
                    "success": True,
                    "data": {
                        "name": user.name,
                        "email": user.email,
                        "access": str(refresh.access_token),
                    },
                },
                status=200,
            )
            response.set_cookie(
                "auth_token",
                refresh.access_token,
                httponly=True,
                samesite="None",
                secure=False,
            )
            return response
        else:
            return Response(
                {"success": False, "error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

    def get(self, request):
        return Response(
            {"success": False, "error": "Only POST method allowed"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
