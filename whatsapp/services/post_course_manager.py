import logging
import os
from django.utils import timezone
from whatsapp.models import UserEnrollment, WhatsappUser
from courses.models import Course
from whatsapp.services.ai_reponse_interpreter import AIResponseInterpreter
from whatsapp.services.enrollment_service import EnrollmentService
from .messaging import WhatsAppService
from typing import Dict

logger = logging.getLogger(__name__)


class PostCourseManager:
    def __init__(self, phone_number_id: str):
        self.phone_number_id = phone_number_id
        self.HAS_SENT_QUESTION = False
        self.interpreter = AIResponseInterpreter(api_key=os.getenv("OPENAI_API_KEY"))
        self.enrollment_service = EnrollmentService()

    STEPS = [
        # {
        #     "type": "message",
        #     "content": "🎉 Congratulations on completing your course! 🎉",
        # },
        {
            "type": "message",
            "content": "Here are some other courses you might like:",
            "action": "list_available_courses",
        },
        {
            "type": "question",
            "content": "Please reply with the number of your chosen course.",
            "ai_context": """You are given a list of course names.
If the user's response is a valid index, return ONLY that index (as a number). 
If the user's response is a course name, match it to the list and return its index number ONLY.
Always return ONLY the index as an integer (e.g., 1, 2, 3).""",
            "property": "active_enrollment",
            "validation": "course_selection",
        },
        {
            "type": "message",
            "content": "✅ You're all set for your next learning journey!",
            "action": "enroll_user",
        },
    ]

    def start(self, user_waid: str):
        try:
            user = WhatsappUser.objects.get(whatsapp_id=user_waid)
            user.post_course_step = 0
            user.post_course_status = "started"
            user.save()
            self._process_step(user)
        except WhatsappUser.DoesNotExist:
            logger.error(f"Post-course flow failed: user {user_waid} not found")
        except Exception as e:
            logger.exception(f"Error starting post-course flow for {user_waid}")

    def handle_response(self, user_waid: str, user_input: str):
        try:
            user = WhatsappUser.objects.get(whatsapp_id=user_waid)
            step = self.STEPS[user.post_course_step]

            conversation_context = self._extract_conversation_context(
                user.post_course_step, user
            )

            print("Conversation context:", conversation_context)

            result = self.interpreter.extract_answer(
                question=conversation_context,
                response=user_input.strip(),
                environment_context="User has completed a course and is choosing a new one. Here we are enrolling user in course. Kindly validate the reponses also.",
            )

            if result["answer"]:
                if not self._validate_response(user, step, result["answer"]):
                    WhatsAppService.send_message(
                        phone_number_id=self.phone_number_id,
                        to=user_waid,
                        message="❌ Invalid selection. Please try again.",
                    )
                    self.HAS_SENT_QUESTION = False
                    return

                user.post_course_step += 1
                user.save()
                self._process_step(user)
            else:
                WhatsAppService.send_message(
                    phone_number_id=self.phone_number_id,
                    to=user_waid,
                    message=result["message_to_user"],
                )

        except Exception:
            logger.exception(f"Error handling post-course response for {user_waid}")

    def _process_step(self, user: WhatsappUser):
        while user.post_course_step < len(self.STEPS):
            step = self.STEPS[user.post_course_step]
            message = step["content"]

            enrolled_courses = self.enrollment_service.get_user_enrollments(user=user)
            print("Enrolled courses", enrolled_courses)
            if step.get("action") == "list_available_courses":
                courses = Course.objects.filter(is_active=True).exclude(
                    course_id__in=enrolled_courses.values_list("course_id", flat=True)
                )[:5]
                if not courses.exists():
                    # ✅ No new courses available → end flow early
                    WhatsAppService.send_message(
                        phone_number_id=self.phone_number_id,
                        to=user.whatsapp_id,
                        message="🎓 You’ve completed all available courses. Stay tuned for new courses soon!",
                    )
                    user.post_course_status = "completed"
                    user.shared_courses_list.clear()
                    user.post_course_completed_at = timezone.now()
                    user.save()
                    return  # stop processing further steps
                course_lines = [
                    f"{i+1}. {c.course_name}" for i, c in enumerate(courses)
                ]
                message = f"{message}\n\n" + "\n".join(course_lines)
                user.shared_courses_list.set(courses)
                user.save()

            elif step.get("action") == "enroll_user":
                if user.active_enrollment:
                    WhatsAppService.send_message(
                        phone_number_id=self.phone_number_id,
                        to=user.whatsapp_id,
                        message=f"📚 You've been enrolled in *{user.active_enrollment.course.course_name}*.",
                    )
                else:
                    WhatsAppService.send_message(
                        phone_number_id=self.phone_number_id,
                        to=user.whatsapp_id,
                        message="⚠️ No course selected.",
                    )

            WhatsAppService.send_message(
                phone_number_id=self.phone_number_id,
                to=user.whatsapp_id,
                message=message,
            )

            if step["type"] == "question":
                self.HAS_SENT_QUESTION = True
                break

            user.post_course_step += 1

            if user.post_course_step >= len(self.STEPS):
                user.post_course_status = "completed"
                user.shared_courses_list.clear()
                user.post_course_completed_at = timezone.now()
                from .course_delivery_manager import CourseDeliveryManager

                course_delivery_manager = CourseDeliveryManager(
                    phone_number_id=self.phone_number_id
                )
                course_delivery_manager.welcome_user_to_course(
                    user_waid=user.whatsapp_id,
                    enrollment=user.active_enrollment,
                )
            user.save()

    def _extract_conversation_context(
        self, current_index: int, user: WhatsappUser
    ) -> list:
        steps = self.STEPS
        context = []
        for i in range(max(0, current_index - 1), current_index + 1):
            message = steps[i].get("content", "")
            enrolled_courses = self.enrollment_service.get_user_enrollments(user=user)
            if steps[i].get("action") == "list_available_courses":
                courses = Course.objects.filter(is_active=True).exclude(
                    course_id__in=enrolled_courses.values_list("course_id", flat=True)
                )[:5]
                course_lines = [
                    f"{i+1}. {c.course_name}" for i, c in enumerate(courses)
                ]
                message = f"{message}\n\n" + "\n".join(course_lines)
            if steps[i].get("ai_context"):
                message += "\n\n" + steps[i]["ai_context"]
            context.append(message)
        return context

    def _validate_response(
        self, user: WhatsappUser, step: Dict, user_input: str
    ) -> bool:
        if step.get("validation") == "course_selection":
            try:
                selected_index = int(str(user_input).strip()) - 1
                courses = list(user.shared_courses_list.all())
                if 0 <= selected_index < len(courses):
                    selected_course = courses[selected_index]
                    enrollment = EnrollmentService.enroll_user_in_course(
                        user=user, course_id=selected_course.course_id
                    )
                    setattr(user, step["property"], enrollment)
                    user.save()
                    return True
                return False
            except (ValueError, IndexError):
                return False
        return True
