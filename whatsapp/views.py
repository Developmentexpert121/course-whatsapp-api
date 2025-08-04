import os
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .services.user import WhatsappUserService
from .services.messaging import WhatsAppService
from .services.onboarding_manager import OnboardingManager
from .services.orientation_manager import OrientationManager
from .models import WhatsappUser

import asyncio
import httpx
import logging
import asyncio

import logging


logger = logging.getLogger(__name__)


def home(request):
    return HttpResponse("Welcome to the WhatsApp Home Page")


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """Webhook verification (GET)"""
        hub_mode = request.query_params.get("hub.mode")
        hub_challenge = request.query_params.get("hub.challenge")
        hub_verify_token = request.query_params.get("hub.verify_token")
        if hub_mode == "subscribe" and hub_verify_token == os.getenv(
            "WHATSAPP_VERIFY_TOKEN"
        ):
            return HttpResponse(hub_challenge, content_type="text/plain", status=200)
        return Response(status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        """Handle incoming WhatsApp message (POST)"""
        try:
            payload = request.data
            logger.info("Received payload: %s", payload)

            # Extract data from webhook payload
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")

            # Verify we have the required phone number ID
            if not phone_number_id:
                logger.error("Missing phone_number_id in payload")
                return Response(
                    {"success": False, "error": "Missing phone_number_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Handle messages
            if "messages" in value:
                message_data = value.get("messages", [{}])[0]
                from_number = message_data.get("from", "")
                message_body = message_data.get("text", {}).get("body", "")
                profile = value.get("contacts", [{}])[0].get("profile", {})
                whatsapp_name = profile.get("name", "Unknown User")

                if not from_number or not message_body:
                    logger.error(
                        "Invalid message data - from: %s, body: %s",
                        from_number,
                        message_body,
                    )
                    return Response(
                        {"success": False, "error": "Invalid message data"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Check if user is in onboarding
                user = WhatsappUser.objects.filter(whatsapp_id=from_number).first()

                if user and user.onboarding_status in ["started", "restarted"]:
                    # Process onboarding response
                    OnboardingManager.process_response(
                        phone_number_id=phone_number_id,
                        user_waid=from_number,
                        user_response=message_body,
                    )
                elif not user or user.onboarding_status == "not_started":
                    # Start new onboarding
                    OnboardingManager.start_onboarding(
                        phone_number_id=phone_number_id,
                        user_waid=from_number,
                        whatsapp_name=whatsapp_name,
                    )

                elif (
                    user.onboarding_status == "completed"
                    and user.orientation_status != "completed"
                ):
                    # will send other messages reply here
                    OrientationManager.handle_orientation_response(
                        phone_number_id=phone_number_id,
                        user_input=message_body,
                        user_waid=from_number,
                    )
                else:
                    print("Here we deliver courses")

                return Response({"success": True}, status=status.HTTP_200_OK)

            # Handle status updates
            elif "statuses" in value:
                status_data = value.get("statuses", [{}])[0]
                logger.info(
                    "Message %s status: %s",
                    status_data.get("id"),
                    status_data.get("status"),
                )
                return Response({"success": True}, status=status.HTTP_200_OK)

            logger.warning("Unhandled payload type: %s", payload)
            return Response(
                {"success": False, "error": "Invalid payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.exception("Error handling WhatsApp webhook POST")
            return Response(
                {"success": False, "error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppUserView(APIView):
    authentication_classes = []  # if no auth needed
    permission_classes = []  # if public
    """API view for WhatsApp user management"""

    def post(self, request):
        """Register or Update a WhatsApp user"""
        data = request.data
        if data.get("whatsapp_id"):
            try:
                user = WhatsappUserService.resgiter_user(data)
                print(user)
                if user and user.get("success"):
                    return Response(
                        {
                            "success": True,
                            "message": "User registered successfully",
                            "data": user.get("data"),
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    raise Exception(user.get("error"))
            except Exception as e:
                logger.exception("Error registering user")
                return Response(
                    {"success": False, "error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            return Response(
                {"success": False, "error": "whatsapp_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get(self, request, whatsapp_id):
        """Retrieve a WhatsApp user by ID"""
        try:
            user = WhatsappUserService.get_user(whatsapp_id)
            if user and user.get("success"):
                return Response(
                    {
                        "success": True,
                        "message": "User fetched successfully",
                        "data": user.get("data"),
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                raise Exception(user.get("error"))
        except WhatsappUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request, whatsapp_id):
        """Update an existing WhatsApp user"""
        data = request.data
        data["whatsapp_id"] = whatsapp_id
        try:
            update_user = WhatsappUserService.update_user(data)
            if update_user and update_user.get("success"):
                return Response(
                    {
                        "success": True,
                        "message": "User updated successfully",
                        "data": update_user.get("data"),
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                raise Exception(update_user.get("error"))
        except WhatsappUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, whatsapp_id):
        """Delete a WhatsApp user by ID"""
        try:
            res = WhatsappUserService.delete_user(whatsapp_id)
            if res and res.get("success"):
                return Response(
                    {
                        "success": True,
                        "message": "User deleted successfully",
                        "data": res.get("data"),
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                raise Exception(res.get("error"))
        except WhatsappUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppUserListView(APIView):
    authentication_classes = []  # if no auth needed
    permission_classes = []  # if public
    """API view for listing all WhatsApp users"""

    def get(self, request):
        """Retrieve all WhatsApp users"""
        try:
            users = WhatsappUserService.get_all_users()
            if users and users.get("success"):
                return Response(
                    {
                        "success": True,
                        "message": "Users list fetched successfully",
                        "data": users.get("data"),
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                raise Exception(users.get("error"))
        except Exception as e:
            logger.exception("Error retrieving users")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request):
        """Delete multiple WhatsApp users"""
        whatsapp_ids = request.data.get("whatsapp_ids", [])
        if not whatsapp_ids:
            return Response(
                {"error": "whatsapp_ids is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            deleted_count = WhatsappUserService.delete_users_bulk(whatsapp_ids)
            if deleted_count and deleted_count.get("success"):
                return Response(
                    {
                        "success": True,
                        "message": "Users list fetched successfully",
                        "data": deleted_count.get("data"),
                    },
                    status=status.HTTP_204_NO_CONTENT,
                )
            else:
                raise Exception(deleted_count.get("error"))
        except Exception as e:
            logger.exception("Error deleting users in bulk")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
