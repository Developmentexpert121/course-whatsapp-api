import asyncio
import logging
import os
from django.utils import timezone
import os
import tempfile
from courses.services.course import CourseService
from whatsapp.models import (
    WhatsappUser,
    UserEnrollment,
    Module,
    Assessment,
    UserAssessmentAttempt,
)
from courses.services.modules import ModuleService
from courses.services.assesments import AssessmentService
from whatsapp.services.assessment_service import UserAssessmentService
from whatsapp.services.cretificates_service import CertificateService
from whatsapp.services.emailing_service import EmailService
from whatsapp.services.module_delivery_service import ModuleDeliveryProgressService
from whatsapp.services.post_course_manager import PostCourseManager
import requests
import tempfile
from .enrollment_service import EnrollmentService
from .messaging import WhatsAppService
from whatsapp.services.ai_reponse_interpreter import AIResponseInterpreter

logger = logging.getLogger(__name__)


def download_temp_file(url: str, suffix=".pdf") -> str:
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in response.iter_content(chunk_size=8192):
            tmp.write(chunk)
        return tmp.name


class CourseDeliveryManager:
    """Manages the delivery of course content and assessments to users"""

    def __init__(self, phone_number_id: str):
        self.phone_number_id = phone_number_id
        self.course_service = CourseService()
        self.module_service = ModuleService()
        self.assessment_service = AssessmentService()
        self.enrollment_service = EnrollmentService()
        self.whatsapp_service = WhatsAppService()
        self.ai_interpreter = AIResponseInterpreter(api_key=os.getenv("OPENAI_API_KEY"))
        self.user_assessment_service = UserAssessmentService()
        self.module_delivery_service = ModuleDeliveryProgressService()
        self.ceritficates_service = CertificateService()
        self.email_service = EmailService()
        self.post_course_manager = PostCourseManager(phone_number_id=phone_number_id)

    def welcome_user_to_course(self, user_waid: str, enrollment: UserEnrollment):
        """Sends a detailed welcome message to the user with course information including modules"""
        course = enrollment.course
        modules = course.modules.all()
        num_modules = modules.count()

        course_name = course.course_name
        category = course.category
        level = course.level
        duration = course.duration_in_weeks
        tags = ", ".join(course.tags) if course.tags else "None"

        welcome_message = (
            f"🎓 *Welcome to the course: {course_name}*\n"
            f"📚 *Category:* {category}\n"
            f"📈 *Level:* {level}\n"
            f"⏳ *Duration:* {duration} week(s)\n"
            f"📦 *Modules:* {num_modules} module(s)\n"
            f"🏷️ *Tags:* {tags}\n\n"
            f" Reply NEXT to continue"
        )

        WhatsAppService.send_message(self.phone_number_id, user_waid, welcome_message)
        UserEnrollment.update_introduction_state(
            enrollment_id=enrollment.id, state="delivering"
        )
        UserEnrollment.increment_intro_step(enrollment_id=enrollment.id)

    def deliver_intro(self, enrollment: UserEnrollment, user_waid: str):
        course = enrollment.course
        modules = course.modules.all()
        module_titles = "\n".join(
            [f"  • {i+1}. {m.title}" for i, m in enumerate(modules)]
        )

        current_step = enrollment.on_intro_step
        res = self.course_service.get_descriptions_by_course_id(
            enrollment.course.course_id
        )

        descriptions = []
        message = ""

        print("DESCRIPTIONS", res.get("data", []))
        if res.get("success"):
            descriptions = res.get("data", [])
            message = (
                f"📖 *Modules Overview:*\n{module_titles}\n\n"
                f"👉 Let's begin your learning journey!\n"
                f"Reply with READY to start the course."
            )

        print(
            f"Length of descriptions:{len(descriptions)}, current_step: {current_step}"
        )

        if len(descriptions) >= current_step:
            next_description = descriptions[current_step - 1]
            images = next_description.get("images", [])
            message = f"{next_description["text"]} \n\n Reply NEXT to continue"
            if images:
                # send multiple images + one message
                self.whatsapp_service.send_images_with_message(
                    phone_number_id=self.phone_number_id,
                    to=user_waid,
                    images=next_description.get("images", []),
                    message=message,
                )
            else:
                # only send the text
                self._send_message(user_waid=user_waid, message=message)

        else:
            # no more descriptions, send modules overview and update state
            message = (
                f"📖 *Modules Overview:*\n{module_titles}\n\n"
                f"👉 Let's begin your learning journey!\n"
                f"Reply with READY to start the course."
            )
            print("[Updating introduction state]: Delivered")
            UserEnrollment.update_introduction_state(
                enrollment_id=enrollment.id, state="delivered"
            )
            enrollment = UserEnrollment.objects.get(id=enrollment.id)  # reload
            enrollment.conversation_state = "offer_quiz_or_content"
            enrollment.save(update_fields=["conversation_state"])

            self._send_message(user_waid=user_waid, message=message)

        UserEnrollment.increment_intro_step(enrollment_id=enrollment.id)

    # --- Main state-loop handler ---

    def process_user_message(self, user_waid: str, user_input: str) -> None:
        user = WhatsappUser.objects.get(whatsapp_id=user_waid)
        enrollment = user.active_enrollment
        current_state = getattr(enrollment, "conversation_state", "idle")

        print("[Current state of enrollment]:", current_state)
        print("[User message]:", user_input)

        # Pure AI intent detection
        intent = self.ai_interpreter.detect_conversation_intent(
            user_input, current_state
        )

        print("[Ai decided intent]:", intent)

        # 1. Greetings/small-talk handling
        if intent == "greeting":
            print("[Sending greeting message]")
            self._send_message(
                user_waid,
                "👋 Hi! I'm your friendly course tutor. Ask me any questions, or type START to continue learning.",
            )

        # 2. Enrollment missing
        if not enrollment:
            print("[handling enrollment missing ]")
            self._handle_no_active_enrollment(user_waid, user)
            return

        # 3. Assessment (no AI help, only accept answers or cancel)
        if enrollment.current_assessment_attempt:
            print("[Handling assessment]")
            if intent == "cancel":
                print("[Handling assessment cancel]")
                self._send_message(
                    user_waid,
                    "Assessment paused. Type 'START' to resume or 'MENU' for options.",
                )
                enrollment.current_assessment_attempt.status = "abandoned"
                enrollment.current_assessment_attempt.save()
                enrollment.current_assessment_attempt = None
                enrollment.conversation_state = "idle"
                enrollment.save()
                return
            print("[Porcessing asessment reponse]")
            self.process_assessment_response(user_waid, user_input)
            return

        if enrollment.introduction != "delivered":
            if intent == "continue":
                self.deliver_intro(enrollment=enrollment, user_waid=user_waid)
            if intent != "continue":
                self._send_message(
                    user_waid,
                    "You're currently in the course introduction. To move ahead, reply with 'CONTINUE'.",
                )
            return
        # 4. State-specific conversational handling
        state = getattr(enrollment, "conversation_state", "idle")

        if state == "awaiting_user_query":
            print(f"[Handling user query][state:{state}]")
            # User can ask a question, or TYPE ready
            if intent == "continue":
                print("[Handling continue confirmation]")
                self._offer_quiz_or_content(user_waid, enrollment)

            elif intent == "question":
                print("[Handling user question]")
                reply = self.answer_user_query(user, enrollment, user_input)
                self._send_message(
                    user_waid,
                    reply
                    + "\n\nType READY when you want to continue, or ask more questions.",
                )
                enrollment.conversation_state = "awaiting_continue_confirmation"
                enrollment.save()

            else:
                print("[Handling unknown]")
                self._send_message(
                    user_waid, "Do you have a question? Or type READY to start!"
                )
            return

        if state == "awaiting_continue_confirmation":
            print(f"[Handling continue confirmation][state:{state}]")
            if intent == "continue":
                print("[Handling continue confirmation]")
                self._offer_quiz_or_content(user_waid, enrollment)
                enrollment.conversation_state = "offer_quiz_or_content"
                enrollment.save()
            else:
                print("[Handling continue cancellation]")
                self._send_message(
                    user_waid,
                    "No worries! Ask any course question, or type READY to continue.",
                )
            return

        if state == "offer_quiz_or_content":
            print(f"[Handling offer quiz or content][state:{state}]")
            # User can request quiz-skip or content\
            if intent == "continue":
                # will check progress
                if enrollment and enrollment.current_module:
                    print("[Enrollment and current module found in enrollment]")
                    module_progress = self.module_delivery_service.get_progress(
                        enrollment=enrollment, module=enrollment.current_module
                    )
                    if module_progress:
                        print(
                            f"[Module progress found with state][{module_progress.state}]"
                        )

                        # if status is topic_delivering then we deliver next topic
                        if module_progress.state == "content_delivering":
                            self.send_next_topic(
                                user_waid=user_waid, enrollment=enrollment
                            )

                        # if status is not started then go with sending first topic
                        if module_progress.state == "not_started":
                            self.send_next_topic(
                                user_waid=user_waid, enrollment=enrollment
                            )

                        # if content_delivered then tell user to go with assessment
                        if module_progress.state == "content_delivered":
                            self._send_message(
                                user_waid=user_waid,
                                message=f"✅ You’ve completed all topics in *{module_progress.module.title}*!\n\n"
                                "Type 'Assessment' to start the module assessment.",
                            )
                    else:
                        print("[Module progress not found]")
                        self._offer_quiz_or_content(
                            user_waid=user_waid, enrollment=enrollment
                        )

                else:
                    print(
                        "[Enrollment not found or current module not found in enrollment]"
                    )
                    self._offer_quiz_or_content(
                        user_waid=user_waid, enrollment=enrollment
                    )
            elif intent == "question":
                self.answer_user_query(
                    user_waid=user_waid, enrollment=enrollment, user_input=user_input
                )

            elif intent == "assessment":
                print("[Handling assessment request]")
                if enrollment.current_module:
                    module_progress = (
                        self.module_delivery_service.get_or_create_progress(
                            enrollment=enrollment, module=enrollment.current_module
                        )
                    )

                    print(module_progress)

                    if module_progress.state == "content_delivered":

                        self.start_module_assessment(user_waid, enrollment)
                        enrollment.conversation_state = "in_assessment"
                        enrollment.save()
                    else:
                        self.start_module_quiz(user_waid, enrollment)
                        enrollment.conversation_state = "in_assessment"
                        enrollment.save()

                else:
                    self._send_message(user_waid, "No Current active module found.")
            elif intent == "module":
                self.start_module(user_waid, enrollment)
            else:
                print("[Handling unknown request]")
                self._send_message(
                    user_waid,
                    "Would you like to begin the module?\nReply **MODULE**. \n\n Or, to take the quiz, \nreply **ASSESSMENT**.",
                )
            return

        # 5. Idle/default
        if state in (None, "", "idle"):
            print(f"[Handling idle][state:{state}]")
            if enrollment.current_module is None:
                print("[Handling no module fersh start of course]")
                self._send_course_introduction(user_waid, enrollment)
                enrollment.conversation_state = "awaiting_user_query"
                enrollment.save()
                return
            else:
                print("[Handling idle]")
                self._send_message(
                    user_waid,
                    f"You're on *{enrollment.current_module.title}*. Do you want to CONTINUE, take a QUIZ to skip, or ask something?",
                )
                enrollment.conversation_state = "offer_quiz_or_content"
                enrollment.save()
                return

        # 6. Clarification fallback
        print(f"[Unknown state][state:{state}]")
        self._send_message(
            user_waid,
            "Sorry, I didn't get that. Type CONTINUE, QUIZ, or ask a question about the course.",
        )

    # ------- Friendly Tutor AI --------

    def answer_user_query(self, user_waid: str, enrollment: UserEnrollment, user_input):
        """
        Use AI to answer user questions based on course/module context.
        This method is kept separate from analyze/extract logic.
        """
        course_name = enrollment.course.course_name
        module_title = (
            enrollment.current_module.title if enrollment.current_module else None
        )

        context = f"""The student is enrolled in the course '{course_name}', 
        course title: {course_name} 
        category: {enrollment.course.category}
        level: {enrollment.course.level}
        description: {enrollment.course.description}        
        ."""
        if module_title:
            context += f"""They are currently on the module '{module_title}'.
            module title: {enrollment.current_module.title}
            content: {enrollment.current_module.content}
            """
            module_delivery = self.module_delivery_service.get_progress(
                enrollment=enrollment, module=enrollment.current_module
            )
            if module_delivery:
                current_topic = module_delivery.current_topic

                if current_topic:
                    context += f"""
                    Have read the topic: '{current_topic.title}'
                    topic title: {current_topic.title}
                    content: {current_topic.content}
                    """

        try:
            ai_prompt = (
                f"{context}\n\n"
                f"The student asked: '{user_input}'\n"
                "Provide a helpful, concise, and clear explanation. "
                "If the question is unrelated or unclear, politely ask them to rephrase and dont answer that unrelated question."
            )

            print("[USER QUESTION PROMPT]:", ai_prompt)

            response = self.ai_interpreter.get_ai_answer(ai_prompt)

            response += "\n\n Type 'Continue' for next topic or 'Repeat' to see the topic again."

            self._send_message(user_waid=user_waid, message=response)
            return (
                response or "That's a great question! Let me get back to you on that."
            )

        except Exception as e:
            logger.error(f"AI query failed: {str(e)}")
            return f"Great question! [The tutor would answer about: {user_input}]"

    # ------- Core Steps & Messaging -------

    def _send_course_introduction(self, user_waid, enrollment):
        course = enrollment.course
        msg = (
            f"🎉 *Welcome to {course.course_name}!* \n\n"
            f"{course.description}\n\n"
            f"Duration: {course.duration_in_weeks} weeks\nLevel: {course.level}\n\n"
            "Do you have any questions before we begin? Ask now, or type READY to start!"
        )
        self._send_message(user_waid, msg)

    def _offer_quiz_or_content(self, user_waid: str, enrollment: UserEnrollment):
        next_module = enrollment.current_module

        if not next_module:
            result = self.enrollment_service.get_next_module(enrollment=enrollment)
            if result["success"]:
                if result["next_module"] is not None:
                    next_module = result["next_module"]
                else:
                    self.complete_module_and_continue()
                    return

        self._send_message(
            user_waid,
            f"✨ Coming up next in your learning path: *{next_module.title}* from the course *{enrollment.course.course_name}*.\n\n"
            "You have two choices:\n\n"
            "📝 *Type QUIZ* – Take a quick test. If you pass, you can skip this module.\n\n"
            "📘 *Type MODULE* – Jump straight into the learning material.\n\n"
            "👉 How would you like to continue?",
        )

        enrollment.conversation_state = "offer_quiz_or_content"
        enrollment.save()

    def send_module_content(self, user_waid, module):
        message = f"📚 *{module.title}*\n\n{module.content}\n\nType 'Next' when you're ready for next topic."
        self._send_message(user_waid, message)

    # Course skip quiz
    def start_module_quiz(self, user_waid, enrollment):
        # Note: implement fetching and starting quiz of type='quiz'
        self._send_message(
            user_waid, "Let’s begin the quiz for this module! Good luck! 🚀"
        )
        # Your quiz assessment start logic here...
        quiz = self.user_assessment_service.get_quiz_for_module(
            module_id=enrollment.current_module
        )
        print(quiz)
        if quiz["success"]:
            print("[Starting quiz]")
            assessment_attempt = self.user_assessment_service.start_assessment(
                enrollment=enrollment,
                assessment_id=quiz["data"].assessment_id,
                user=enrollment.user,
            )
            self.user_assessment_service.send_next_question(
                assessment_attempt.id, self.phone_number_id
            )
            self.module_delivery_service.mark_quiz_delivered(
                enrollment=enrollment, module=enrollment.current_module
            )
        else:
            print("[No Quiz found]")
            self._send_message(user_waid, "No quiz available for this module.")

    # Start module assessment
    def start_module_assessment(self, user_waid, enrollment):
        # Note: implement fetching and starting quiz of type='quiz'
        self._send_message(
            user_waid, "Let’s begin the Assessment for this module! Good luck! 🚀"
        )
        # Your quiz assessment start logic here...
        assessment = self.user_assessment_service.get_assessment_for_module(
            module_id=enrollment.current_module
        )
        print(assessment)
        if assessment["success"]:
            print("[Starting Assessment]")
            assessment_attempt = self.user_assessment_service.start_assessment(
                enrollment=enrollment,
                assessment_id=assessment["data"].assessment_id,
                user=enrollment.user,
            )
            self.user_assessment_service.send_next_question(
                assessment_attempt.id, self.phone_number_id
            )
            self.module_delivery_service.mark_assessment_delivered(
                enrollment=enrollment, module=enrollment.current_module
            )
        else:
            print("[No Assessment found]")
            self._send_message(user_waid, "No quiz available for this module.")

    def process_assessment_response(self, user_waid: str, response: str) -> None:
        """Process user's response to an assessment question with detailed logging"""
        try:
            logger.info(f"Starting assessment response processing for user {user_waid}")
            logger.debug(f"Raw user response: {response}")

            # Get user and enrollment
            user = WhatsappUser.objects.get(whatsapp_id=user_waid)
            logger.debug(f"Found user: {user.id} | Phone: {user.whatsapp_id}")

            enrollment = user.active_enrollment
            if not enrollment:
                logger.warning(f"No active enrollment for user {user_waid}")
                self._send_message(
                    user_waid, "⚠️ No active assessment. Type 'MENU' to see options."
                )
                return

            if not enrollment.current_assessment_attempt:
                logger.warning(f"No active assessment attempt for user {user_waid}")
                self._send_message(
                    user_waid, "⚠️ No active assessment. Type 'MENU' to see options."
                )
                return

            attempt = enrollment.current_assessment_attempt
            logger.info(
                f"Processing attempt {attempt.id} | "
                f"Current question: {attempt.current_question_index} | "
                f"Questions answered: {attempt.questions_answered}"
            )

            # Evaluate the question response
            logger.debug(
                f"Evaluating question response for assessment {attempt.assessment.assessment_id}"
            )
            evaluation_result = (
                self.user_assessment_service.evaluate_question_for_assessment(
                    assessment_id=attempt.assessment.assessment_id,
                    question_index=attempt.current_question_index,
                    user_input=response,
                    attempt_id=attempt.id,
                )
            )
            logger.debug(f"Evaluation result: {evaluation_result}")

            # Update attempt progress
            attempt.questions_answered += 1
            attempt.current_question_index += 1
            attempt.save()
            logger.info(
                f"Updated attempt {attempt.id} | "
                f"New question index: {attempt.current_question_index} | "
                f"Total answered: {attempt.questions_answered}"
            )

            # Send next question
            logger.debug("Preparing to send next question...")
            next_question_result = self.user_assessment_service.send_next_question(
                attempt.id, phone_number_id=self.phone_number_id
            )

            if next_question_result is None:
                self.complete_assessment(user_waid, attempt=attempt)
                logger.info(f"Assessment {attempt.id} completed successfully")
            else:
                logger.debug(f"Sent next question: {next_question_result}")

        except WhatsappUser.DoesNotExist:
            logger.error(f"User not found with WA ID: {user_waid}")
            self._send_message(user_waid, "⚠️ Account error. Please contact support.")

        except Exception as e:
            logger.exception(
                f"Critical error processing assessment response from {user_waid}"
            )
            self._send_message(
                user_waid, "⚠️ Failed to process your answer. Please try again."
            )
            # Re-raise if you want the error to propagate up
            # raise

    def complete_assessment(
        self, user_waid: str, attempt: UserAssessmentAttempt
    ) -> None:
        """Complete the assessment attempt and provide feedback"""
        try:
            user = attempt.user
            # Get all questions and responses
            questions = attempt.assessment.questions.all()
            responses = attempt.responses.all()

            # Assessment complete
            score = (
                sum((r.score if r.is_correct else 0) for r in responses)
                if responses
                else 0
            )
            total = len(questions)

            # Update attempt status
            attempt.status = "completed"
            attempt.score = score
            attempt.completed_at = timezone.now()
            attempt.passed = (
                attempt.score / total * 100
            ) >= 70  # 70% passing threshold
            attempt.save()

            # # Send completion message
            # message = (
            #     f"🎉 Assessment complete!\n\n"
            #     f"Your score: {score}/{total}\n"
            #     f"Success rate: {round(score/total*100)}%\n\n"
            #     f"Type 'MENU' to return to main options."
            # )
            # WhatsAppService.send_message(self.phone_number_id, user_waid, message)

            enrollment = attempt.enrollment

            # Send results
            message = f"📝 *Assessment Complete!*\n\n"
            message += f"Score: {attempt.score}\n"
            message += (
                f"Result: {'Passed ✅' if attempt.passed else 'Try Again ❌'}\n\n"
            )

            if attempt.passed:
                enrollment.current_assessment_attempt = None
                enrollment.conversation_state = "offer_quiz_or_content"
                enrollment.save()

                module_progress = self.module_delivery_service.get_or_create_progress(
                    enrollment=enrollment, module=enrollment.current_module
                )

                if module_progress.state == "assessment_delivered":
                    self.module_delivery_service.mark_assessment_completed(
                        enrollment=enrollment, module=enrollment.current_module
                    )
                elif module_progress.state == "quiz_delivered":
                    self.module_delivery_service.mark_quiz_completed(
                        enrollment=enrollment, module=enrollment.current_module
                    )
                result = self.enrollment_service.get_next_module(enrollment=enrollment)
                next_module = None
                if result["success"]:
                    if result["next_module"] is not None:
                        next_module = result["next_module"]
                        message += f"Great job! Moving to the next module *{next_module.title}*"
                        self._send_message(user_waid, message)
                        self.complete_module_and_continue(user_waid, attempt.module)
                    else:
                        self.complete_module_and_continue(user_waid, attempt.module)
                        return
            else:
                # TODO: implementation pending
                enrollment.current_assessment_attempt = None
                enrollment.conversation_state = "offer_quiz_or_content"
                enrollment.save()

                message += "Would you like to try again? (Reply YES or NO)"
                self._send_message(user_waid, message)

        except Exception as e:
            logger.exception(f"Failed to complete assessment for {user_waid}")
            self._send_message(
                user_waid, "⚠️ Failed to complete assessment. Please try again."
            )

    def start_module(self, user_waid: str, enrollment: UserEnrollment) -> None:
        """Start the next module for the user by sending its content"""
        try:
            # Get the next module from enrollment (which should already be set)
            current_module = enrollment.current_module
            if current_module is None:
                result = self.enrollment_service.get_next_module(enrollment)
                if result["success"]:
                    if result["next_module"] is not None:
                        current_module = result["next_module"]
                        enrollment.current_module = current_module
                        self.module_delivery_service.get_or_create_progress(
                            enrollment=enrollment, module=current_module
                        )
                        enrollment.save()

            if not current_module:
                self._send_message(user_waid, "⚠️ No next module found.")
                return

            print("[Starting next module]:", current_module.title)

            # Send the module content to the user
            # self.module_delivery_service.mark_content_delivered(
            #     enrollment=enrollment, module=current_module
            # )
            self.send_module_content(user_waid, current_module)
            self.module_delivery_service.reset_progress(enrollment=enrollment)

            # self.send_next_topic(user_waid, enrollment)

        except Exception as e:
            logger.exception(f"Failed to start next module for {user_waid}")
            self._send_message(
                user_waid, "⚠️ Failed to start next module. Please try again."
            )

    def send_next_topic(self, user_waid: str, enrollment: UserEnrollment):
        module = enrollment.current_module
        if not module:
            self._send_message(user_waid, "⚠️ No active module found.")
            return

        progress = self.module_delivery_service.deliver_next_topic(enrollment, module)

        if progress.current_topic:
            topic = progress.current_topic
            message = (
                f"📖 *{module.title} - {topic.title}*\n\n{topic.content}\n\n"
                "Type 'Continue' for next or 'Repeat' to see again."
            )
            self._send_message(user_waid, message)

        elif progress.state == "content_delivered":
            # All topics done
            self._send_message(
                user_waid,
                f"✅ You’ve completed all topics in *{module.title}*!\n\n"
                "Type 'Assessment' to start the module assessment.",
            )

    def complete_module_and_continue(self, user_waid: str, module: Module) -> None:
        """Complete the current module and move to the next one"""
        try:
            user = WhatsappUser.objects.get(whatsapp_id=user_waid)
            enrollment = user.active_enrollment

            if not enrollment:
                return self._handle_no_active_enrollment(user_waid, user)

            # Calculate progress
            all_modules = self.module_service.get_all_modules(
                course_id=enrollment.course.course_id
            )

            if not all_modules["success"] or not all_modules["data"]:
                self._send_message(user_waid, "⚠️ Failed to load course modules.")
                return

            total_modules = len(all_modules["data"])
            current_order = module.order
            next_order = current_order + 1

            # Find next module
            next_module_data = next(
                (m for m in all_modules["data"] if m["order"] == next_order), None
            )

            if next_module_data:
                next_module = Module.objects.get(module_id=next_module_data["moduleId"])
                enrollment.current_module = next_module
                enrollment.progress = next_order / total_modules
                enrollment.conversation_state = "offer_quiz_or_content"
                enrollment.save()
                self.module_delivery_service.get_or_create_progress(
                    enrollment=enrollment, module=enrollment.current_module
                )

                self._offer_quiz_or_content(user_waid, enrollment)
            else:
                # Course completed
                self.complete_course(user_waid, enrollment)

        except Exception as e:
            logger.exception(f"Failed to complete module for {user_waid}")
            self._send_message(
                user_waid, "⚠️ Failed to move to next module. Please try again."
            )

    def complete_course(self, user_waid: str, enrollment: UserEnrollment) -> None:
        """Mark course as completed and provide certificate"""
        try:
            enrollment.status = "completed"
            enrollment.completed = True
            enrollment.progress = 1.0
            enrollment.certificate_earned = True
            enrollment.certificate_id = f"CERT-{enrollment.id.hex[:8].upper()}"
            enrollment.completed_at = timezone.now()
            enrollment.save()

            certificate_url = self.ceritficates_service.generate_and_upload_certificate(
                enrollment=enrollment
            )

            # Clear active enrollment
            user = enrollment.user
            user.active_enrollment = None
            user.save()

            # Send completion message
            message = f"🎉 *Course Completed!*\n\n"
            message += f"Congratulations on completing course: {enrollment.course.course_name}!\n\n"
            message += "Type 'COURSES' to see other available courses."

            self._send_message(user_waid, message)

            self.whatsapp_service.send_file(
                self.phone_number_id,
                user.whatsapp_id,
                file_url=certificate_url,
                filename=f"certificate_{enrollment.course.course_name}",
            )

            if user.email:
                subject = f"🎓 Your Certificate for {enrollment.course.course_name}"
                body = (
                    f"Dear {user.full_name},\n\n"
                    f"Congratulations on completing the course *{enrollment.course.course_name}*!\n\n"
                    "Attached is your certificate of completion.\n\n"
                    "Keep learning!\nWAppStudy Team"
                )

                temp_file_path = None
                try:
                    # Download certificate locally
                    temp_file_path = download_temp_file(certificate_url, suffix=".pdf")

                    # Send email with attachment
                    self.email_service.send_email_with_file(
                        subject=subject,
                        body=body,
                        to=[user.email],
                        attachments=[temp_file_path],
                    )

                except Exception:
                    logger.exception(
                        f"Failed to send certificate email to {user.email}"
                    )
                finally:
                    # Cleanup local file
                    if temp_file_path and os.path.exists(temp_file_path):
                        os.remove(temp_file_path)

            self.post_course_manager.start(user_waid=user_waid)

        except Exception as e:
            logger.exception(f"Failed to complete course for {user_waid}")
            self._send_message(
                user_waid, "⚠️ Failed to complete course. Please contact support."
            )

    # -- Fallbacks and utility handlers --

    def _handle_no_active_enrollment(self, user_waid, user):
        enrollments = self.enrollment_service.get_user_enrollments(user=user)
        # if enrollments.exists():
        #     message = f"📚 *Your Enrolled Courses*\n\nHello {user.whatsapp_name}, please select a course:\n\n"
        #     for idx, enrollment in enumerate(enrollments, start=1):
        #         progress = int(enrollment.progress * 100)
        #         status = (
        #             "In Progress" if enrollment.status == "in_progress" else "Completed"
        #         )
        #         message += f"{idx}. *{enrollment.course.course_name}*\n"
        #         message += f"   - Progress: {progress}%\n"
        #         message += f"   - Status: {status}\n\n"
        #     message += "Reply with the number of the course you want to continue."
        #     self._send_message(user_waid, message)
        # else:
        message = (
            f"👋 Hello {user.whatsapp_name},\n\n"
            "You're not enrolled in any courses yet.\n\n"
        )
        self._send_message(user_waid, message)
        self.post_course_manager.start(user_waid=user_waid)

    def _send_message(self, user_waid: str, message: str) -> None:
        self.whatsapp_service.send_message(
            phone_number_id=self.phone_number_id, to=user_waid, message=message
        )
