# services/topics.py
import logging
from typing import Optional, Dict, List
from django.db import transaction
from authentication import models
from courses.models import Topic, Module

logger = logging.getLogger(__name__)


class TopicService:
    @classmethod
    def to_dict(cls, topic: Topic) -> Dict:
        """Convert Topic model instance to JSON-friendly dictionary"""
        return {
            "topicId": str(topic.topic_id),
            "moduleId": str(topic.module.module_id),
            "title": topic.title,
            "content": topic.content,
            "order": topic.order, 
            "isActive": topic.is_active,
            "createdAt": topic.created_at.isoformat(),
            "updatedAt": topic.updated_at.isoformat(),
        }

    @classmethod
    def get_topics_by_module(cls, module_id: str) -> Dict:
        """Retrieve all topics for a specific module"""
        try:
            topics = Topic.objects.filter(
                module__module_id=module_id, is_active=True
            ).order_by("order")
            return {
                "success": True,
                "data": [cls.to_dict(topic) for topic in topics],
            }
        except Exception as e:
            logger.exception(f"Error retrieving topics for module {module_id}")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def get_topic(cls, topic_id: str) -> Dict:
        """Retrieve a specific topic by ID"""
        try:
            topic = Topic.objects.get(topic_id=topic_id)
            return {"success": True, "data": cls.to_dict(topic)}
        except Topic.DoesNotExist:
            return {"success": False, "data": None, "error": "Topic not found"}
        except Exception as e:
            logger.exception(f"Error retrieving topic {topic_id}")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def create_or_update_topic(
        cls, module_id: str, topic_id: Optional[str], data: Dict
    ) -> Dict:
        """Create or update a topic, handling order assignment"""
        try:
            module = Module.objects.get(module_id=module_id)
            
            with transaction.atomic():
                # If creating a new topic, determine the next available order
                if not topic_id:
                    max_order = Topic.objects.filter(module=module).aggregate(
                        models.Max("order")
                    )["order__max"] or 0
                    data["order"] = data.get("order", max_order + 1)
                
                # Create or update the topic
                topic, created = Topic.objects.update_or_create(
                    topic_id=topic_id if topic_id else None,
                    defaults={
                        "module": module,
                        "title": data.get("title"),
                        "content": data.get("content"),
                        "order": data.get("order"),
                        "is_active": data.get("is_active", True),
                    },
                )
                
                # If order was changed, reorder other topics if needed
                if "order" in data:
                    cls._renumber_topics(module)
                
                action = "created" if created else "updated"
                return {
                    "success": True,
                    "data": cls.to_dict(topic),
                    "message": f"Topic {action} successfully",
                }
                
        except Module.DoesNotExist:
            return {"success": False, "data": None, "error": "Module not found"}
        except Exception as e:
            logger.exception(f"Error creating/updating topic {topic_id}")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def delete_topic(cls, topic_id: str) -> Dict:
        """Delete a topic and optionally renumber siblings"""
        try:
            with transaction.atomic():
                topic = Topic.objects.get(topic_id=topic_id)
                module = topic.module
                topic.delete()
                
                # Renumber remaining topics
                cls._renumber_topics(module)
                
                return {
                    "success": True,
                    "message": "Topic deleted successfully",
                    "data": topic_id,
                }
        except Topic.DoesNotExist:
            return {"success": False, "error": "Topic not found"}
        except Exception as e:
            logger.exception(f"Error deleting topic {topic_id}")
            return {"success": False, "error": str(e)}

    @classmethod
    def reorder_topics(cls, module_id: str, ordered_topic_ids: List[str]) -> Dict:
        """Reorder topics based on a list of topic IDs (for drag/drop)"""
        try:
            module = Module.objects.get(module_id=module_id)
            
            with transaction.atomic():
                # Update the order of each topic based on its position in the list
                for new_order, topic_id in enumerate(ordered_topic_ids, start=1):
                    Topic.objects.filter(
                        topic_id=topic_id, module=module
                    ).update(order=new_order)
                
                return {
                    "success": True,
                    "message": "Topics reordered successfully",
                }
        except Module.DoesNotExist:
            return {"success": False, "error": "Module not found"}
        except Exception as e:
            logger.exception(f"Error reordering topics for module {module_id}")
            return {"success": False, "error": str(e)}

    @classmethod
    def _renumber_topics(cls, module: Module) -> None:
        """Helper method to renumber topics in a module sequentially"""
        topics = Topic.objects.filter(module=module).order_by("order")
        for order, topic in enumerate(topics, start=1):
            if topic.order != order:
                topic.order = order
                topic.save()