import logging
from django.utils import timezone
from courses.models import Module
from whatsapp.models import UserEnrollment
from whatsapp.models import ModuleDeliveryProgress

logger = logging.getLogger(__name__)


class ModuleDeliveryProgressService:
    @staticmethod
    def get_or_create_progress(
        enrollment: UserEnrollment, module: Module
    ) -> ModuleDeliveryProgress:
        """
        Ensure there is a ModuleDeliveryProgress entry for this enrollment & module.
        """
        progress, created = ModuleDeliveryProgress.objects.get_or_create(
            enrollment=enrollment, module=module
        )
        if created:
            logger.info(f"Created new progress entry for {enrollment.user} - {module}")
        return progress

    @staticmethod
    def update_state(
        enrollment: UserEnrollment, module: Module, new_state: str
    ) -> ModuleDeliveryProgress:
        """
        Update the state of module delivery progress for a given enrollment & module.
        """
        progress = ModuleDeliveryProgressService.get_or_create_progress(
            enrollment, module
        )
        old_state = progress.state
        progress.state = new_state
        progress.last_updated = timezone.now()
        progress.save()

        logger.info(
            f"Module '{module}' for user {enrollment.user} updated from '{old_state}' to '{new_state}'"
        )
        return progress

    @staticmethod
    def get_modules_by_state(enrollment: UserEnrollment, state: str):
        """
        Return all modules for a given enrollment that match the given state.
        """
        return ModuleDeliveryProgress.objects.filter(enrollment=enrollment, state=state)

    @staticmethod
    def reset_progress(enrollment: UserEnrollment):
        """
        Reset all module progress states for a given enrollment.
        """
        ModuleDeliveryProgress.objects.filter(enrollment=enrollment).update(
            state="not_started", last_updated=timezone.now()
        )
        logger.info(f"Reset module progress for user {enrollment.user}")

    @staticmethod
    def mark_content_delivered(enrollment: UserEnrollment, module: Module):
        return ModuleDeliveryProgressService.update_state(
            enrollment, module, "content_delivered"
        )

    @staticmethod
    def mark_quiz_delivered(enrollment: UserEnrollment, module: Module):
        return ModuleDeliveryProgressService.update_state(
            enrollment, module, "quiz_delivered"
        )

    @staticmethod
    def mark_quiz_completed(enrollment: UserEnrollment, module: Module):
        return ModuleDeliveryProgressService.update_state(
            enrollment, module, "quiz_completed"
        )

    @staticmethod
    def mark_assessment_delivered(enrollment: UserEnrollment, module: Module):
        return ModuleDeliveryProgressService.update_state(
            enrollment, module, "assessment_delivered"
        )

    @staticmethod
    def mark_assessment_completed(enrollment: UserEnrollment, module: Module):
        return ModuleDeliveryProgressService.update_state(
            enrollment, module, "assessment_completed"
        )
