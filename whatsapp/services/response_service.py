from courses.models import UserQuestionResponse


class ResponseService:

    @staticmethod
    def record_response(attempt, question, user_answer, is_correct):
        return UserQuestionResponse.objects.create(
            attempt=attempt,
            question=question,
            question_text_snapshot=question.question_text,
            question_type_snapshot=question.question_type,
            options_snapshot=question.options,
            correct_answer_snapshot=question.correct_answer,
            user_answer=user_answer,
            is_correct=is_correct,
        )
