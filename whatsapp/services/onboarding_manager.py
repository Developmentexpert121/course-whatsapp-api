import logging
import os
import httpx
from whatsapp.models import WhatsappUser
from django.utils import timezone

from whatsapp.services.ai_reponse_interpreter import AIResponseInterpreter
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
                "Welcome to WAppStudy! 🎓\n\n"
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
    def process_response(
        cls, phone_number_id: str, user_waid: str, user_response: str
    ) -> httpx.Response:
        """Process user's response to onboarding questions"""
        try:
            user = WhatsappUser.objects.get(whatsapp_id=user_waid)
            current_step = user.onboarding_step

            if current_step >= len(cls.ONBOARDING_QUESTIONS):
                return cls._complete_onboarding(phone_number_id, user_waid)

            # Save response to user profile
            question = cls.ONBOARDING_QUESTIONS[current_step]["question"]

            result = cls.interpreter.extract_answer(
                question=question,
                response=user_response.strip(),
                environment_context="User is currently answering onboarding phase questions. Kindly validate the reponses also",
            )
            if result["answer"]:
                property_name = cls.ONBOARDING_QUESTIONS[current_step]["property"]
                setattr(user, property_name, result["answer"])
                user.onboarding_step += 1
                user.save()

                # Send next question or completion
                if user.onboarding_step < len(cls.ONBOARDING_QUESTIONS):
                    next_question = cls.ONBOARDING_QUESTIONS[user.onboarding_step][
                        "question"
                    ]
                    question_num = user.onboarding_step + 1
                    message = f"{question_num}. {next_question}"
                else:
                    return cls._complete_onboarding(phone_number_id, user_waid)

                return WhatsAppService.send_message(
                    phone_number_id=phone_number_id, to=user_waid, message=message
                )
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
