from datetime import datetime
from ..models import WhatsappUser, UserEnrollment


class UserProgressService:
    @staticmethod
    def get_user_current_state(user):
        """Get comprehensive current state of a user"""
        active_enrollments = (
            UserEnrollment.objects.filter(user=user, status="in_progress")
            .prefetch_related("course", "current_module", "current_assessment_attempt")
            .order_by("-last_accessed")
        )

        current_courses = []
        for enrollment in active_enrollments:
            course_data = {
                "enrollment_id": str(enrollment.id),
                "course_id": str(enrollment.course_id),
                "course_name": enrollment.course.course_name,
                "progress": enrollment.progress,
                "current_module": {
                    "module_id": str(enrollment.current_module_id),
                    "title": (
                        enrollment.current_module.title
                        if enrollment.current_module
                        else None
                    ),
                },
                "current_assessment": None,
            }

            if enrollment.current_assessment_attempt:
                attempt = enrollment.current_assessment_attempt
                course_data["current_assessment"] = {
                    "attempt_id": str(attempt.id),
                    "assessment_id": str(attempt.assessment_id),
                    "title": attempt.assessment.title,
                    "progress": (attempt.questions_answered / attempt.total_questions)
                    * 100,
                    "current_question_index": attempt.current_question_index,
                }

            current_courses.append(course_data)

        return {
            "user_id": str(user.id),
            "whatsapp_id": user.whatsapp_id,
            "current_courses": current_courses,
            "last_active": user.last_active,
        }

    @staticmethod
    def resume_user_progress(user, enrollment_id):
        """Resume a user's progress from where they left off"""
        enrollment = UserEnrollment.objects.get(id=enrollment_id, user=user)

        # Update last accessed timestamp
        enrollment.last_accessed = datetime.now()
        enrollment.save()

        user.last_active = datetime.now()
        user.save()

        if enrollment.current_assessment_attempt:
            attempt = enrollment.current_assessment_attempt
            return {
                "type": "assessment",
                "assessment_id": str(attempt.assessment_id),
                "attempt_id": str(attempt.id),
                "current_question_index": attempt.current_question_index,
                "total_questions": attempt.total_questions,
            }
        else:
            return {
                "type": "module",
                "module_id": str(enrollment.current_module_id),
                "module_title": enrollment.current_module.title,
                "course_id": str(enrollment.course_id),
            }
