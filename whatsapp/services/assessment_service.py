from django.db import transaction
from datetime import datetime
from ..models import (
    UserAssessmentAttempt,
    UserQuestionResponse,
    Assessment,
    AssessmentQuestion,
)


class AssessmentService:
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
