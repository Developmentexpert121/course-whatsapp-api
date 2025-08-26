# services/topics.py
import uuid
import logging
from typing import Optional, Dict, List
from django.db import transaction
from courses.models import Topic, Module
from django.db.models import Max , Case, When, IntegerField, F    

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
        """Create or update a topic, handling order assignment safely."""
        try:
            print("99----7-----7----7----7---7---7---7----7---7----7----7----")
            module = Module.objects.get(module_id=module_id)
            with transaction.atomic():
                # ---------- CREATE path ----------
                if not topic_id:
                    provided_order = data.get("order", None)
                    if provided_order is None:
                        max_order = (
                            Topic.objects.filter(module=module)
                            .aggregate(max_order=Max("order"))
                        )["max_order"] or 0
                        order_value = max_order + 1
                    else:
                        order_value = int(provided_order)
                        if order_value < 1:
                            order_value = 1

                    topic = Topic.objects.create(
                        module=module,
                        title=(data.get("title") or ""),
                        content=(data.get("content") or ""),
                        order=order_value,                     # << use order_value here
                        is_active=data.get("is_active", True),
                    )
                    created = True

                    # If client explicitly supplied an order, renumber to insert correctly
                    if provided_order is not None:
                        cls._renumber_topics(module)

                # ---------- UPDATE path ----------
                else:
                    defaults = {}
                    if "title" in data:
                        defaults["title"] = data.get("title")
                    if "content" in data:
                        defaults["content"] = data.get("content")
                    if "is_active" in data:
                        defaults["is_active"] = data.get("is_active")
                    if "order" in data and data.get("order") is not None:
                        defaults["order"] = int(data.get("order"))

                    # keep module reference consistent
                    defaults["module"] = module

                    topic, created = Topic.objects.update_or_create(
                        topic_id=topic_id,
                        defaults=defaults,
                    )

                    if "order" in data and data.get("order") is not None:
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
        """Reorder topics safely using positive temporary offsets (avoids negative values)."""
        try:
            module = Module.objects.get(module_id=module_id)
        except Module.DoesNotExist:
            return {"success": False, "error": "Module not found"}
        try:
            if not isinstance(ordered_topic_ids, list) or len(ordered_topic_ids) == 0:
                return {"success": False, "error": "orderedTopicIds must be a non-empty list"}

            # normalize & validate UUIDs
            cleaned_ids = []
            for raw_id in ordered_topic_ids:
                if not isinstance(raw_id, str):
                    return {"success": False, "error": f"Invalid topic id: {raw_id}"}
                raw_id = raw_id.strip()
                try:
                    tid = uuid.UUID(raw_id)
                    cleaned_ids.append(tid)
                except ValueError:
                    return {"success": False, "error": f"Invalid topic id format: {raw_id}"}

            # ensure provided IDs belong to this module
            module_qs = Topic.objects.filter(module=module)
            existing_ids = set(module_qs.values_list("topic_id", flat=True))
            provided_set = set(cleaned_ids)
            missing = provided_set - existing_ids
            if missing:
                missing_str = ", ".join(str(x) for x in missing)
                return {"success": False, "error": f"The following topic(s) do not belong to module {module_id}: {missing_str}"}

            # compute a safe positive temporary base > current max order
            current_max = module_qs.aggregate(max_order=Max("order"))["max_order"] or 0
            # ensure temp_base is strictly greater than any existing order
            temp_base = int(current_max) + len(cleaned_ids) + 5

            # Two-phase update inside a transaction
            with transaction.atomic():
                # Phase 1: move mapped topics to unique temporary high values
                for new_order, tid in enumerate(cleaned_ids, start=1):
                    temp_value = temp_base + new_order
                    Topic.objects.filter(module=module, topic_id=tid).update(order=temp_value)

                # Phase 2: set final desired orders for mapped topics
                for new_order, tid in enumerate(cleaned_ids, start=1):
                    Topic.objects.filter(module=module, topic_id=tid).update(order=new_order)

                # Final safety: renumber the entire module to ensure contiguous ordering
                cls._renumber_topics(module)

            return {"success": True, "message": "Topics reordered successfully"}

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
                
                
    @classmethod
    def duplicate_topic(cls, topic_id: str, dest_module_id: Optional[str] = None) -> Dict:
        """
        Duplicate a single topic. If dest_module_id is provided, duplicate into that module,
        otherwise duplicate into the same module (as a sibling).
        Returns the duplicated topic dict on success.
        """
        try:
            src_topic = Topic.objects.get(topic_id=topic_id)

            # determine destination module
            if dest_module_id:
                try:
                    dest_module = Module.objects.get(module_id=dest_module_id)
                except Module.DoesNotExist:
                    return {"success": False, "error": "Destination module not found"}
            else:
                dest_module = src_topic.module

            with transaction.atomic():
                # compute new order at destination
                current_max = (
                    Topic.objects.filter(module=dest_module).aggregate(max_order=Max("order"))["max_order"]
                    or 0
                )
                new_order = int(current_max) + 1

                duplicated = Topic.objects.create(
                    module=dest_module,
                    title=f"{src_topic.title} (Copy)",
                    content=src_topic.content,
                    order=new_order,
                    is_active=src_topic.is_active,
                )

                # ensure contiguous ordering (defensive)
                cls._renumber_topics(dest_module)

            return {"success": True, "data": cls.to_dict(duplicated), "message": "Topic duplicated successfully"}
        except Topic.DoesNotExist:
            return {"success": False, "data": None, "error": "Source topic not found"}
        except Exception as e:
            logger.exception(f"Error duplicating topic {topic_id}")
            return {"success": False, "data": None, "error": str(e)}
