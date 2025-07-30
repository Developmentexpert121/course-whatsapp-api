from django.db import transaction
from datetime import datetime
from ..models import UserEnrollment, Course, Module


class EnrollmentService:
    @staticmethod
    def enroll_user_in_course(user, course_id):
        """Enroll a user in a new course"""
        course = Course.objects.get(pk=course_id)
        first_module = course.modules.order_by("order").first()

        with transaction.atomic():
            enrollment = UserEnrollment.objects.create(
                user=user,
                course=course,
                current_module=first_module,
                enrollment_date=datetime.now(),
                last_accessed=datetime.now(),
            )
            return enrollment

    @staticmethod
    def get_user_enrollment(user, course_id):
        """Get a user's enrollment for a specific course"""
        try:
            return UserEnrollment.objects.get(user=user, course_id=course_id)
        except UserEnrollment.DoesNotExist:
            return None

    @staticmethod
    def update_enrollment_progress(enrollment, new_module=None):
        """Update user's progress in a course"""
        if new_module:
            enrollment.current_module = new_module
            enrollment.current_assessment_attempt = None  # Clear any active assessment

        # Calculate progress (simplified - you might want a more sophisticated calculation)
        total_modules = enrollment.course.modules.count()
        completed_modules = enrollment.course.modules.filter(
            order__lt=(
                new_module.order if new_module else enrollment.current_module.order
            )
        ).count()
        enrollment.progress = min(100, (completed_modules / total_modules) * 100)

        enrollment.last_accessed = datetime.now()
        enrollment.save()
        return enrollment

    @staticmethod
    def complete_course(enrollment):
        """Mark a course as completed for the user"""
        enrollment.completed = True
        enrollment.status = "completed"
        enrollment.progress = 100
        enrollment.last_accessed = datetime.now()
        enrollment.save()
        return enrollment

    @staticmethod
    def get_active_enrollments(user):
        """Get all active enrollments for a user"""
        return UserEnrollment.objects.filter(user=user, status="in_progress").order_by(
            "-last_accessed"
        )
