import logging
import os
from whatsapp.models import WhatsappUser
from courses.models import Course  # Replace with your actual course model
from django.utils import timezone

from whatsapp.services.ai_reponse_interpreter import AIResponseInterpreter
from whatsapp.services.enrollment_service import EnrollmentService
from .messaging import WhatsAppService
from typing import Dict

logger = logging.getLogger(__name__)


class OrientationManager:
    """Handles the user orientation process with multiple steps"""

    HAS_SENT_QUESTION = False

    interpreter = AIResponseInterpreter(api_key=os.getenv("OPENAI_API_KEY"))

    # Define orientation steps - can be messages or questions
    ORIENTATION_STEPS = [
        {
            "type": "message",
            "content": "📘 *Welcome to the Orientation!*\n\nHere are a few things you can do:\n"
            "- Type *HELP* for assistance.\n"
            "- Type *COURSES* to see available courses.\n"
            "- Type *PROGRESS* to view your progress.",
        },
        {
            "type": "message",
            "content": "Let's get started by choosing a course. Here are your options:",
            "action": "list_courses",  # Special action to list courses
        },
        {
            "type": "question",
            "content": "Please reply with the your chosen course.",
            "ai_context": """You are given a list of course names.
If the user's response is a valid index, return ONLY that index (as a number). Do NOT return the course name.
If the user's response is a course name, match it against the list. If matched, return its index number ONLY.Always return ONLY the index as an integer (e.g., 1, 2, 3), nothing else.""",
            "property": "active_enrollment",
            "validation": "course_selection",
        },
        {
            "type": "message",
            "content": "🎉 Great choice! Here's some important information about how our courses work...",
            "action": "enroll_user",  # Special action to enroll user
        },
        {
            "type": "message",
            "content": "✅ Orientation complete! You're now ready to start learning.",
        },
    ]

    @classmethod
    def start_orientation(cls, phone_number_id: str, user_waid: str) -> None:
        """Start orientation process"""
        try:
            user = WhatsappUser.objects.get(whatsapp_id=user_waid)
            user.orientation_status = "started"
            user.orientation_step = 0
            user.save()

            # Send first orientation step
            cls._process_step(phone_number_id, user)

        except WhatsappUser.DoesNotExist:
            logger.error(f"Orientation failed: user {user_waid} not found")
        except Exception as e:
            logger.exception(f"Error starting orientation for {user_waid}")

    @classmethod
    def extract_conversation_context(cls, current_index: int) -> list:
        """
        Extracts all messages between the last question and the current question step.

        Args:
            steps (list): The full list of steps (like ORIENTATION_STEPS).
            current_index (int): The index of the latest question asked.

        Returns:
            list: A list of message/question strings forming the context.
        """
        steps = cls.ORIENTATION_STEPS
        context = []
        i = current_index - 1

        # Go backward to find the last question
        while i >= 0:
            if steps[i].get("type") == "question":
                break
            i -= 1

        # Extract steps from last question + 1 to current_index
        start_index = i + 1
        for step in steps[start_index:current_index]:
            if step.get("type") in ["message", "question"]:

                message = step.get("content", "")
                ai_context = step.get("ai_context", "")
                if step.get("action") == "list_courses":
                    courses = Course.objects.filter(is_active=True)[:5]
                    course_lines = [
                        f"{i+1}. {course.course_name}"
                        for i, course in enumerate(courses)
                    ]
                    message = f"{message}\n\n" + "\n".join(course_lines)
                if ai_context:
                    print("Ai context found:", ai_context)
                    message += "\n\n" + ai_context
                context.append(message)

        # Add the current question (latest)
        if steps[current_index].get("type") == "question":
            ai_context = steps[current_index].get("ai_context", "")
            content = steps[current_index].get("content", "")
            if ai_context:
                content += "\n\n" + ai_context
            context.append(content)

        return context

    @classmethod
    def handle_orientation_response(
        cls, phone_number_id: str, user_waid: str, user_input: str
    ) -> None:
        """Handle user response during orientation"""
        try:
            user = WhatsappUser.objects.get(whatsapp_id=user_waid)
            current_step = user.orientation_step

            if current_step >= len(cls.ORIENTATION_STEPS):
                logger.warning(f"User {user_waid} orientation already completed")
                return

            step = cls.ORIENTATION_STEPS[current_step]

            # # Validate response if it's a question step
            # if step["type"] == "question":

            conversation_context = cls.extract_conversation_context(current_step)

            print("Conversation Context: ", conversation_context)

            result = cls.interpreter.extract_answer(
                question=conversation_context,
                response=user_input.strip(),
                environment_context="User is currently answering orientation phase questions. Here we are enrolling user in course. Kindly validate the reponses also.",
            )

            if result["answer"]:

                print("Asnwer from AI: ", result["answer"])
                if not cls._validate_response(user, step, result["answer"]):
                    # Validation failed - don't advance step, send error message
                    WhatsAppService.send_message(
                        phone_number_id=phone_number_id,
                        to=user_waid,
                        message="❌ Invalid input. Please try again.",
                    )
                    # Once response has been recieved for question, make it ready to send next list of messages.
                    cls.HAS_SENT_QUESTION = False
                    return

                # Advance to next step
                user.orientation_step += 1

                print("Orinetation step from response: ", user.orientation_step)
                if user.orientation_step + 1 >= len(cls.ORIENTATION_STEPS):
                    user.orientation_status = "completed"
                    user.orientation_completed_at = timezone.now()
                user.save()

                # Process next step
                cls._process_step(phone_number_id, user)
            else:
                return WhatsAppService.send_message(
                    phone_number_id=phone_number_id,
                    to=user_waid,
                    message=result["message_to_user"],
                )

        except Exception as e:
            logger.exception(f"Error handling orientation response for {user_waid}")

    @classmethod
    def _process_step(cls, phone_number_id: str, user: WhatsappUser) -> None:
        """Process the current orientation step"""

        while user.orientation_step < len(cls.ORIENTATION_STEPS):
            step = cls.ORIENTATION_STEPS[user.orientation_step]
            message = step["content"]

            # Special actions
            if step.get("action") == "list_courses":
                courses = Course.objects.filter(is_active=True)[:5]
                course_lines = [
                    f"{i+1}. {course.course_name}" for i, course in enumerate(courses)
                ]
                message = f"{message}\n\n" + "\n".join(course_lines)
                user.shared_courses_list.set(courses)
                user.save()
            elif step.get("action") == "enroll_user":
                if user.active_enrollment:
                    # Example: perform enrollment (you can expand this)

                    WhatsAppService.send_message(
                        phone_number_id=phone_number_id,
                        to=user.whatsapp_id,
                        message=f"✅ You've been enrolled in *{user.active_enrollment.course.course_name}*.",
                    )
                else:
                    WhatsAppService.send_message(
                        phone_number_id=phone_number_id,
                        to=user.whatsapp_id,
                        message="⚠️ No course selected. Cannot enroll.",
                    )
                pass

            # Send message
            WhatsAppService.send_message(
                phone_number_id=phone_number_id,
                to=user.whatsapp_id,
                message=message,
            )

            if step["type"] == "question":
                cls.HAS_SENT_QUESTION = True
                break  # Stop here and wait for user response

            user.orientation_step += 1
            print("Orientation step from process:", user.orientation_step)
            if user.orientation_step >= len(cls.ORIENTATION_STEPS):
                user.orientation_status = "completed"
                user.shared_courses_list.clear()
                user.orientation_completed_at = timezone.now()
            user.save()

    @classmethod
    def _validate_response(
        cls, user: WhatsappUser, step: Dict, user_input: str
    ) -> bool:
        """Validate user response based on step requirements"""
        validation_type = step.get("validation")

        if validation_type == "course_selection":
            try:
                selected_index = (
                    int(user_input.strip() if type(user_input) == "str" else user_input)
                    - 1
                )
                courses = list(user.shared_courses_list.all())
                if selected_index < 0 or selected_index >= len(courses):
                    return False

                # Store selected course if validation passes
                selected_course = courses[selected_index]
                enrollment = EnrollmentService.enroll_user_in_course(
                    user=user, course_id=selected_course.course_id
                )
                setattr(user, step["property"], enrollment)
                user.save()
                return True
            except (ValueError, IndexError):
                return False

        # Add other validation types as needed
        return True  # Default to valid if no specific validation
