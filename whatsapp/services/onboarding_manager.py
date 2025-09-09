from datetime import timedelta
import logging
import os
import random
import httpx
from whatsapp.models import WhatsappUser
from django.utils import timezone

from whatsapp.services.ai_reponse_interpreter import AIResponseInterpreter
from whatsapp.services.emailing_service import EmailService
from .messaging import WhatsAppService
from .orientation_manager import OrientationManager

logger = logging.getLogger(__name__)


class OnboardingManager:
    """Manages the user onboarding process"""

    ONBOARDING_QUESTIONS = [
        {"question": "What is your full name?", "property": "full_name"},
        {"question": "What is your email address?", "property": "email"},
    ]

    interpreter = AIResponseInterpreter(api_key=os.getenv("OPENAI_API_KEY"))

    @classmethod
    def generate_otp(cls):
        return str(random.randint(100000, 999999))

    @classmethod
    def start_onboarding(
        cls, phone_number_id: str, user_waid: str, whatsapp_name: str
    ) -> httpx.Response:
        """Initiate the onboarding process"""
        try:
            # Create/update user record
            user, created = WhatsappUser.objects.get_or_create(
                whatsapp_id=user_waid,
                defaults={
                    "whatsapp_name": whatsapp_name,
                    "onboarding_status": "started",
                    "onboarding_step": 0,
                    "last_active": timezone.now(),
                    "registration_date": timezone.now(),
                },
            )

            # Send welcome message
            welcome_msg = (
                "Welcome to Nikkoworkx! 🎓\n\n"
                "Let's get you registered. Please answer these questions:\n\n"
                f"1. {cls.ONBOARDING_QUESTIONS[0]['question']}"
            )

            WhatsAppService.send_message(
                phone_number_id=phone_number_id, to=user_waid, message=welcome_msg
            )

            if not created:
                user.onboarding_status = "restarted"
                user.onboarding_step = 0
                user.save()

        except Exception as e:
            logger.exception(f"Failed to start onboarding for {user_waid}")
            raise

    @classmethod
    def process_response(cls, phone_number_id: str, user_waid: str, user_response: str):
        try:
            user = WhatsappUser.objects.get(whatsapp_id=user_waid)
            current_step = user.onboarding_step

            # OTP handling flow
            if user.email and not user.email_verified:
                return cls._handle_email_verification(
                    phone_number_id, user, user_response.strip()
                )

            # Normal onboarding questions
            if current_step >= len(cls.ONBOARDING_QUESTIONS):
                return cls._complete_onboarding(phone_number_id, user_waid)

            question = cls.ONBOARDING_QUESTIONS[current_step]["question"]

            result = cls.interpreter.extract_answer(
                question=question,
                response=user_response.strip(),
                environment_context="User is answering onboarding questions. Validate the response.",
            )

            if result["answer"]:
                property_name = cls.ONBOARDING_QUESTIONS[current_step]["property"]
                setattr(user, property_name, result["answer"])

                # Special handling for email → send OTP
                if property_name == "email":
                    otp = cls.generate_otp()
                    user.otp_code = otp
                    user.otp_expires_at = timezone.now() + timedelta(minutes=10)
                    user.otp_attempts = 0
                    user.save()

                    body = f"Your OTP code is: {otp}. It expires in 10 minutes."

                    EmailService.send_simple_email("Your OTP", body, [user.email])

                    return WhatsAppService.send_message(
                        phone_number_id=phone_number_id,
                        to=user_waid,
                        message="We’ve sent a 6-digit code to your email. "
                        "Please reply with the code here.\n\n"
                        "Type 'RESEND' to get a new code or 'CHANGE EMAIL' to update your email.",
                    )

                # Continue if not email step
                user.onboarding_step += 1
                user.save()
                if user.onboarding_step < len(cls.ONBOARDING_QUESTIONS):
                    next_question = cls.ONBOARDING_QUESTIONS[user.onboarding_step][
                        "question"
                    ]
                    return WhatsAppService.send_message(
                        phone_number_id=phone_number_id,
                        to=user_waid,
                        message=next_question,
                    )
                else:
                    return cls._complete_onboarding(phone_number_id, user_waid)

            else:
                return WhatsAppService.send_message(
                    phone_number_id=phone_number_id,
                    to=user_waid,
                    message=result["message_to_user"],
                )

        except WhatsappUser.DoesNotExist:
            logger.error(f"User {user_waid} not found for onboarding")
            raise ValueError("User not in onboarding process")
        except Exception as e:
            logger.exception(f"Failed to process response from {user_waid}")
            raise

    @classmethod
    def _handle_email_verification(cls, phone_number_id, user, response: str):
        """Handle OTP entry / resend / change email"""
        if response.upper() == "RESEND":
            otp = cls.generate_otp()
            user.otp_code = otp
            user.otp_expires_at = timezone.now() + timedelta(minutes=10)
            user.save()

            body = f"Your OTP code is: {otp}. It expires in 10 minutes."

            EmailService.send_simple_email("Your OTP", body, [user.email])
            return WhatsAppService.send_message(
                phone_number_id,
                user.whatsapp_id,
                "✅ A new OTP has been sent to your email.",
            )

        if response.upper() == "CHANGE EMAIL":
            user.email = None
            user.email_verified = False
            user.onboarding_step = 1  # back to email question
            user.save()
            return WhatsAppService.send_message(
                phone_number_id,
                user.whatsapp_id,
                "Please provide your new email address:",
            )

        # Normal OTP entry
        if (
            user.otp_code
            and response == user.otp_code
            and user.otp_expires_at > timezone.now()
        ):
            user.email_verified = True
            user.otp_code = None
            user.save()

            user.onboarding_step += 1
            user.save()

            WhatsAppService.send_message(
                phone_number_id, user.whatsapp_id, "✅ Email verified successfully! 🎉"
            )
            cls.process_response(phone_number_id, user.whatsapp_id, "")
        else:
            user.otp_attempts += 1
            user.save()
            return WhatsAppService.send_message(
                phone_number_id,
                user.whatsapp_id,
                "❌ Invalid or expired code. Please try again, type 'RESEND' for a new code, "
                "or 'CHANGE EMAIL' to use a different email.",
            )

    @classmethod
    def _complete_onboarding(
        cls, phone_number_id: str, user_waid: str
    ) -> httpx.Response:
        """Mark onboarding as complete and send confirmation"""
        user = WhatsappUser.objects.get(whatsapp_id=user_waid)
        user.onboarding_status = "completed"
        user.onboarding_completed_at = timezone.now()

        user.save()

        completion_msg = (
            "🎉 Registration complete! Thank you.\n\n"
            "You'll now receive study materials and updates.\n"
            "Type 'HELP' anytime for assistance."
        )

        WhatsAppService.send_message(
            phone_number_id=phone_number_id, to=user_waid, message=completion_msg
        )

        return OrientationManager.start_orientation(phone_number_id, user.whatsapp_id)
