from django.db import transaction
from datetime import datetime
from ..models import UserEnrollment, Course, Module, WhatsappUser


class EnrollmentService:
    @staticmethod
    def enroll_user_in_course(user: WhatsappUser, course_id: str):
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
    def get_user_enrollments(user: WhatsappUser):
        """Get all enrollments for a user"""
        try:
            return UserEnrollment.objects.filter(user=user)
        except UserEnrollment.DoesNotExist:
            return None

    @staticmethod
    def update_enrollment_progress(enrollment: UserEnrollment, new_module=None):
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
    def complete_course(enrollment: UserEnrollment):
        """Mark a course as completed for the user"""
        enrollment.completed = True
        enrollment.status = "completed"
        enrollment.progress = 100
        enrollment.last_accessed = datetime.now()
        enrollment.save()
        return enrollment

    @staticmethod
    def get_active_enrollment(user: WhatsappUser):
        """Get active enrollment for a user"""
        return user.active_enrollment

    @classmethod
    def get_next_module(cls, enrollment: UserEnrollment):
        """Get the next module for an enrollment"""
        try:
            print("enrollment found: ", enrollment)
            current_module = enrollment.current_module
            print("current module:", current_module)

            if not current_module:
                # Return the first module in order
                next_module = enrollment.course.modules.order_by("order").first()
            else:
                # Return the next module with higher order
                next_module = (
                    enrollment.course.modules.filter(order__gt=current_module.order)
                    .order_by("order")
                    .first()
                )

            if not next_module:
                print(f"No next module found for enrollment: {enrollment.id}")
                # Optionally mark course as completed or trigger certificate
                return {"next_module": None, "success": True}

            print("next module:", next_module)
            return {"next_module": next_module, "success": True}

        except Exception as e:
            print(f"Error getting next module for enrollment {enrollment.id}")
            return {"next_module": None, "success": False, "error": str(e)}
