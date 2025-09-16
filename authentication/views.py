import secrets
import string
from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from whatsapp.services.emailing_service import EmailService
from .models import User

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


class AdminView(APIView):
    authentication_classes = []
    permission_classes = []

    def generate_password(self, length=12):
        characters = string.ascii_letters + string.digits + string.punctuation
        return "".join(secrets.choice(characters) for _ in range(length))

    def post(self, request):
        name = request.data.get("name")
        email = request.data.get("email")

        if not email or not name:
            return Response(
                {"success": False, "error": "Name and email are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ✅ Check if user already exists
        if User.objects.filter(email=email).exists():
            return Response(
                {"success": False, "error": "User with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate secure password
        password = self.generate_password(10)

        try:
            # ✅ Create user without raw password
            new_user = User.objects.create(email=email, name=name, password=password)

            new_user.save()

            # Send email
            email_body = (
                "Hi, you have been invited to Nikkoworkx.ai \n\n"
                "Here are your login credentials:\n"
                f"Email: {email}\n"
                f"Password: {password}\n"
            )

            EmailService.send_simple_email(
                subject="You have been invited to Nikkoworkx.ai",
                body=email_body,
                to=[email],
            )

            return Response(
                {"success": True, "message": "User created and credentials sent"},
                status=status.HTTP_201_CREATED,
            )

        except IntegrityError:
            return Response(
                {"success": False, "error": "User with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            return Response(
                {"success": False, "error": "Failed to create user"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request):
        try:
            admins = User.objects.values("name", "email")
            if admins and len(admins) > 0:
                return Response(
                    {
                        "success": True,
                        "data": admins,
                        "message": "Admins fetched successfully",
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"success": False, "error": "No admin found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Exception as e:
            return Response(
                {"success": False, "error": "Fetch failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ResendCredentials(APIView):
    authentication_classes = []  # Disable auth for login
    permission_classes = []  # Allow any user to access

    def generate_password(self, length=10):
        import string, random

        chars = string.ascii_letters + string.digits + string.punctuation
        return "".join(random.choice(chars) for _ in range(length))

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response(
                {"success": False, "error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_user = User.objects.filter(email=email).first()
            if not new_user:
                return Response(
                    {"success": False, "error": "User does not exist"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Generate secure password
            password = self.generate_password(10)
            new_user.password = password
            new_user.save()

            # Send email
            email_body = (
                "Here are your login credentials for Nikkoworkx.ai:\n"
                f"Email: {email}\n"
                f"Password: {password}\n"
            )
            EmailService.send_simple_email(
                subject="Login credentials for Nikkoworkx.ai",
                body=email_body,
                to=[email],
            )

            return Response(
                {"success": True, "message": "Credentials sent"},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            print("Unexpected error:", str(e))
            return Response(
                {"success": False, "error": "Failed to send credentials"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
