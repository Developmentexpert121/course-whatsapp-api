from django.utils import timezone
from django.db.models import Max
from courses.models import Module, Topic
from whatsapp.models import UserEnrollment, ModuleDeliveryProgress
import logging

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
    def get_progress(
        enrollment: UserEnrollment, module: Module
    ) -> ModuleDeliveryProgress | None:
        """
        Return the existing ModuleDeliveryProgress entry for this enrollment & module.
        Does not create a new one.
        """
        try:
            return ModuleDeliveryProgress.objects.get(
                enrollment=enrollment, module=module
            )
        except ModuleDeliveryProgress.DoesNotExist:
            return None

    @staticmethod
    def deliver_next_topic(
        enrollment: UserEnrollment, module: Module
    ) -> ModuleDeliveryProgress:
        """
        Deliver the next topic in the module for the given enrollment.
        Updates current_topic and state.
        """
        progress = ModuleDeliveryProgressService.get_or_create_progress(
            enrollment, module
        )

        # If no topics in this module
        topics = module.topics.filter(is_active=True).order_by("order")
        if not topics.exists():
            logger.warning(f"No active topics found in module {module.title}")
            return progress

        if progress.current_topic:
            # Find the next topic after current one
            next_topic = topics.filter(order__gt=progress.current_topic.order).first()
        else:
            # Start with the first topic
            next_topic = topics.first()

        if next_topic:
            progress.current_topic = next_topic
            progress.state = "content_delivering"  # still delivering content
            progress.last_updated = timezone.now()
            progress.save()
            logger.info(
                f"Delivered topic '{next_topic.title}' in module '{module.title}' to {enrollment.user}"
            )
        else:
            # No more topics left → mark module as fully delivered
            progress.current_topic = None
            progress.state = "content_delivered"
            progress.last_updated = timezone.now()
            progress.save()
            logger.info(
                f"All topics delivered for module '{module.title}' (user {enrollment.user})"
            )

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
        return ModuleDeliveryProgress.objects.filter(enrollment=enrollment, state=state)

    @staticmethod
    def reset_progress(enrollment: UserEnrollment):
        ModuleDeliveryProgress.objects.filter(enrollment=enrollment).update(
            state="not_started", current_topic=None, last_updated=timezone.now()
        )
        logger.info(f"Reset module progress for user {enrollment.user}")

    # Quiz/Assessment states (unchanged)
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
