import logging
import os
from django.db import transaction
from datetime import datetime
from django.utils import timezone

from whatsapp.serializers import UserAssessmentAttemptSerializer
from whatsapp.services.ai_reponse_interpreter import AIResponseInterpreter
from whatsapp.services.messaging import WhatsAppService
from ..models import (
    UserAssessmentAttempt,
    UserQuestionResponse,
    Assessment,
    AssessmentQuestion,
)


logger = logging.getLogger(__name__)


class UserAssessmentService:

    ai_interpreter = AIResponseInterpreter(api_key=os.getenv("OPENAI_API_KEY"))

    @staticmethod
    def get_user_assessments(user):
        """Retrieve all WhatsApp users"""
        try:
            assessment_attempts = UserAssessmentAttempt.objects.all()
            return {
                "success": True,
                "data": UserAssessmentAttemptSerializer(
                    assessment_attempts, many=True
                ).data,
            }
        except Exception as e:
            logger.exception("Error retrieving users")
            return {"success": False, "data": None, "error": str(e)}

    @staticmethod
    def start_assessment(user, enrollment, assessment_id):
        """Start a new assessment attempt"""
        assessment = Assessment.objects.get(pk=assessment_id)

        with transaction.atomic():
            attempt = UserAssessmentAttempt.objects.create(
                user=user,
                enrollment=enrollment,
                assessment=assessment,
                module=assessment.module,
                total_questions=assessment.questions.count(),
                started_at=datetime.now(),
            )

            # Update enrollment to point to this attempt
            enrollment.current_assessment_attempt = attempt
            enrollment.save()

            return attempt

    @staticmethod
    def get_current_question(attempt):
        """Get the current question the user should answer"""
        if attempt.current_question_index >= attempt.total_questions:
            return None

        questions = attempt.assessment.questions.order_by("pk")
        return questions[attempt.current_question_index]

    @staticmethod
    def record_response(attempt, question_id, user_answer):
        """Record user's response to a question"""
        question = AssessmentQuestion.objects.get(pk=question_id)

        # Determine if answer is correct (simplified - adjust based on your logic)
        is_correct = False
        if question.type == "mcq":
            is_correct = (
                user_answer.strip().lower() == question.correct_answer.strip().lower()
            )
        # Add other question type handling as needed

        with transaction.atomic():
            # Create response record
            UserQuestionResponse.objects.create(
                attempt=attempt,
                question=question,
                question_text_snapshot=question.question_text,
                question_type_snapshot=question.type,
                options_snapshot=question.options if question.type == "mcq" else None,
                correct_answer_snapshot=question.correct_answer,
                user_answer=user_answer,
                is_correct=is_correct,
                answered_at=datetime.now(),
            )

            # Update attempt progress
            attempt.questions_answered += 1
            attempt.current_question_index += 1

            if attempt.current_question_index >= attempt.total_questions:
                attempt.status = "completed"
                attempt.completed_at = datetime.now()
                # Calculate score
                correct_count = attempt.responses.filter(is_correct=True).count()
                attempt.score = (correct_count / attempt.total_questions) * 100
                attempt.passed = attempt.score >= 70  # Assuming 70% passing score

            attempt.save()
            return attempt

    @staticmethod
    def complete_assessment(attempt):
        """Finalize assessment completion"""
        if attempt.status != "completed":
            attempt.status = "completed"
            attempt.completed_at = datetime.now()
            attempt.save()

        # Update enrollment to point back to module
        enrollment = attempt.enrollment
        enrollment.current_assessment_attempt = None
        enrollment.save()

        return attempt

    @staticmethod
    def get_user_assessment_history(user, course_id=None):
        """Get all assessment attempts for a user, optionally filtered by course"""
        queryset = UserAssessmentAttempt.objects.filter(user=user).order_by(
            "-started_at"
        )
        if course_id:
            queryset = queryset.filter(enrollment__course_id=course_id)
        return queryset

    @classmethod
    def get_assessment_for_module(cls, module_id: str):
        assessment = Assessment.objects.filter(
            module_id=module_id, is_active=True, type="assessment"
        ).first()
        return {"success": True, "data": assessment}

    @classmethod
    def get_quiz_for_module(cls, module_id: str):
        quiz = Assessment.objects.filter(
            module_id=module_id, is_active=True, type="quiz"
        ).first()
        if quiz:
            return {"success": True, "data": quiz}
        else:
            return {"success": False, "message": "Quiz not found"}

    @classmethod
    def get_questions_for_assessment(cls, assessment_id: str):
        questions = AssessmentQuestion.objects.filter(assessment_id=assessment_id)
        return {"success": True, "data": [cls.to_dict(q) for q in questions]}

    # Evaluation of answer
    @classmethod
    def evaluate_question_for_assessment(
        cls, assessment_id: str, question_index: int, user_input: str, attempt_id: str
    ):
        """Evaluate a question for an assessment and save the response"""
        try:
            assessment = Assessment.objects.get(assessment_id=assessment_id)
            attempt = UserAssessmentAttempt.objects.get(id=attempt_id)
            question = assessment.questions.all()[question_index]

            # Evaluate the question
            result = cls.evaluate_question(question, user_input)

            question_score = result["score"] * question.marks

            # Save the response
            UserQuestionResponse.objects.create(
                attempt=attempt,
                question=question,
                question_text_snapshot=question.question_text,
                question_type_snapshot=question.type,
                options_snapshot=(
                    question.options if hasattr(question, "options") else None
                ),
                correct_answer_snapshot=result["correct_answer"],
                user_answer=user_input,
                is_correct=result["success"],
                score=question_score,
                answered_at=timezone.now(),
            )

            return result

        except IndexError:
            raise ValueError("Invalid question index")
        except Assessment.DoesNotExist:
            raise ValueError("Assessment not found")
        except UserAssessmentAttempt.DoesNotExist:
            raise ValueError("Assessment attempt not found")
        except Exception as e:
            print(f"Error evaluating question: {str(e)}")
            raise

    @classmethod
    def evaluate_question(cls, question, user_input):
        """Evaluate a question with AI fallback"""
        try:
            if question.type == "mcq":
                return cls.evaluate_multiple_choice_question(
                    question,
                    user_input,
                    use_ai_fallback=True,  # Enable AI for ambiguous MCQ answers
                )
            elif question.type == "open":
                return cls.evaluate_short_answer_question(
                    question,
                    user_input,
                    use_ai=True,  # Enable AI for open-ended questions
                    similarity_threshold=0.7,  # Slightly lower threshold for open answers
                )
            else:
                raise ValueError(f"Unknown question type: {question.type}")

        except Exception as e:
            print(f"Error evaluating question {question.id}: {str(e)}")
            return {
                "success": False,
                "message": "Error evaluating your answer",
                "score": 0,
            }

    @classmethod
    def evaluate_multiple_choice_question(
        cls, question: AssessmentQuestion, user_input, use_ai_fallback=False
    ):
        """
        Evaluate a multiple choice question with numeric/index or text-based input.
        """

        # Identify correct option
        correct_option = next(
            (opt for opt in question.options if opt["isCorrect"]), None
        )
        options_list = [opt["text"] for opt in question.options]

        # Step 1: Convert numeric input to option text (if valid)
        stripped_input = user_input.strip()
        if stripped_input.isdigit():
            index = int(stripped_input) - 1
            if 0 <= index < len(question.options):
                user_input = question.options[index]["text"]

        # Step 2: Case-insensitive exact match with correct answer
        if (
            correct_option
            and user_input.strip().lower() == correct_option["text"].lower()
        ):
            return {
                "success": True,
                "message": "Correct answer!",
                "score": 1,
                "user_answer": user_input,
                "correct_answer": correct_option["text"],
            }

        # Step 3: AI fallback if enabled
        if use_ai_fallback:
            return cls.ai_interpreter._ai_evaluate_response(
                question=question.question_text,
                options=options_list,
                correct_answer=correct_option["text"] if correct_option else "",
                user_input=user_input,
            )

        # Step 4: Default incorrect response
        return {
            "success": False,
            "message": f"Incorrect answer. The correct answer was: {correct_option['text']}",
            "score": 0,
            "user_answer": user_input,
            "correct_answer": correct_option["text"] if correct_option else "",
        }

    @classmethod
    def evaluate_short_answer_question(
        cls, question, user_input, use_ai=True, similarity_threshold=0.8
    ):
        """
        Evaluate a short answer question with AI-powered flexible matching.

        Args:
            question: Question object with correct_answer
            user_input: User's text response
            use_ai: Whether to use AI for flexible evaluation
            similarity_threshold: Confidence threshold for AI evaluation (0-1)

        Returns:
            Evaluation dict with success, message, and score
        """
        # First try exact matching (case-insensitive)
        if user_input.strip().lower() == question.correct_answer.lower():
            return {
                "success": True,
                "message": "Correct answer!",
                "score": 1,
                "user_answer": user_input,
                "correct_answer": question.correct_answer,
                "is_ai_corrected": False,
            }

        # If exact match fails and AI evaluation is enabled
        if use_ai:
            return cls.ai_interpreter._ai_evaluate_short_answer(
                question_text=question.text,
                user_answer=user_input,
                correct_answer=question.correct_answer,
                threshold=similarity_threshold,
            )

        # Default incorrect response
        return {
            "success": False,
            "message": f"Incorrect. The correct answer was: {question.correct_answer}",
            "score": 0,
            "user_answer": user_input,
            "correct_answer": question.correct_answer,
            "is_ai_corrected": False,
        }

    # Send next question to user
    @classmethod
    def send_next_question(cls, attempt_id: str, phone_number_id):
        """
        Sends the next question in the assessment to the user.
        Handles completion when no more questions remain.
        """
        try:
            attempt = UserAssessmentAttempt.objects.select_related("assessment").get(
                id=attempt_id
            )
            user = attempt.user
            assessment = attempt.assessment

            # Get all questions and responses
            questions = assessment.questions.all()
            responses = attempt.responses.all()

            # Find the next unanswered question
            next_index = len(responses)

            if next_index >= len(questions):

                return None

            # Get next question
            next_question = questions[next_index]

            # Format question based on type
            if next_question.type == "mcq":
                options = "\n".join(
                    f"{i+1}. {opt['text']}"
                    for i, opt in enumerate(next_question.options)
                )
                message = (
                    f"Question {next_index+1}/{len(questions)}:\n"
                    f"{next_question.question_text}\n\n"
                    f"Options:\n{options}\n\n"
                    f"Reply with the NUMBER of your answer."
                )
            else:
                message = (
                    f"Question {next_index+1}/{len(questions)}:\n"
                    f"{next_question.question_text}\n\n"
                    f"Please type your answer."
                )

            # Send question via WhatsApp
            WhatsAppService.send_message(phone_number_id, user.whatsapp_id, message)

            # Return question info (optional)
            return {
                "question_index": next_index,
                "question_id": str(next_question.question_id),
                "question_type": next_question.type,
            }

        except UserAssessmentAttempt.DoesNotExist:
            logger.error(f"Attempt not found: {attempt_id}")
            raise ValueError("Assessment attempt not found")
        except Exception as e:
            logger.error(f"Error sending next question: {str(e)}")
            raise ValueError("Error processing next question")

    @classmethod
    def to_dict(cls, question):
        return {
            "question_id": str(question.question_id),
            "type": question.type,
            "question_text": question.question_text,
            "options": question.options,
            "marks": question.marks,
        }
