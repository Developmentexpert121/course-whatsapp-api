import logging
import uuid
from courses.models import Course, Module, Topic, TopicParagraph
from .topics import TopicService
from typing import Dict, Any, Optional
from django.db.models import Max
from django.db import transaction

logger = logging.getLogger(__name__)


class ModuleService:
    @classmethod
    def to_dict(cls, module, include_topics: bool = False):
        """Convert Module model instance to dictionaryoptionally including topics"""
        module_dict = {
            "moduleId": module.module_id,
            "courseId": module.course.course_id,
            "title": module.title,
            "content": module.content,
            "order": module.order,
            "createdAt": module.created_at,
            "updatedAt": module.updated_at,
        }

        if include_topics:
            topics_result = TopicService.get_topics_by_module(str(module.module_id))
            if topics_result["success"]:
                module_dict["topics"] = topics_result["data"]
            else:
                module_dict["topics"] = []

        return module_dict

    @classmethod
    def get_all_modules(cls, course_id=None):
        """Retrieve all modules or modules for a specific course"""
        try:
            if course_id:
                modules = Module.objects.filter(course__course_id=course_id).order_by(
                    "order"
                )
            else:
                modules = Module.objects.all()
            return {
                "success": True,
                "data": [cls.to_dict(module) for module in modules],
            }
        except Exception as e:
            logger.exception("Error retrieving modules")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def get_module(cls, module_id, include_topics=False):
        """Retrieve a module by ID, optionally including topics"""
        try:
            module = Module.objects.get(module_id=module_id)
            return {"success": True, "data": cls.to_dict(module, include_topics)}
        except Module.DoesNotExist:
            return {"success": False, "data": None, "error": "Module not found"}
        except Exception as e:
            logger.exception(f"Error retrieving module {module_id}")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def create_or_update_module(cls, module_id, course_id, data: Dict[str, Any]):
        """Create or update a module. If `topics` array is present in `data`,
        sync topics for the created/updated module transactionally.

        Expected topic item keys (frontend):
          - topicId (optional): existing topic UUID string for updates
          - title
          - content (optional)
          - order (optional)
          - isActive (optional)
        """
        try:
            course = Course.objects.get(course_id=course_id)
            # maintain previous behaviour (you were toggling course is_active earlier)
            course.is_active = False
            course.save()

            with transaction.atomic():
                module, created = Module.objects.update_or_create(
                    module_id=module_id,
                    defaults={
                        "course": course,
                        "title": data.get("title"),
                        "content": data.get("content"),
                        "order": data.get("order", 0),
                    },
                )

                # If frontend sent topics array, sync them
                topics_payload = data.get("topics", None)
                if isinstance(topics_payload, list):
                    # Normalize items (dict with keys we expect)
                    normalized = []
                    for item in topics_payload:
                        if not isinstance(item, dict):
                            continue
                        raw_is_active = None
                        if "isActive" in item:
                            raw_is_active = item.get("isActive")
                        elif "is_active" in item:
                            raw_is_active = item.get("is_active")

                        # coerce to True/False (treat None as True)
                        if raw_is_active is None:
                            is_active_val = True
                        else:
                            # if client sends "false"/"true" strings also handle that defensively
                            if isinstance(raw_is_active, str):
                                is_active_val = raw_is_active.lower() in (
                                    "1",
                                    "true",
                                    "yes",
                                )
                            else:
                                is_active_val = bool(raw_is_active)

                        normalized.append(
                            {
                                "topicId": item.get("topicId") or item.get("topic_id"),
                                "title": item.get("title", "") or "",
                                "content": item.get("content", "") or "",
                                "order": item.get("order"),
                                "is_active": is_active_val,
                            }
                        )

                    # Fetch existing topic queryset for this module
                    existing_qs = Topic.objects.filter(module=module)

                    # Build set of provided existing ids (UUID objects)
                    provided_existing_ids = set()
                    for it in normalized:
                        if it["topicId"]:
                            try:
                                provided_existing_ids.add(uuid.UUID(str(it["topicId"])))
                            except Exception:
                                # ignore invalid UUID formats (could log if desired)
                                pass

                    # Optionally delete topics that exist on server but not in provided list
                    # Only perform deletion if the request included at least one existing topic id
                    if provided_existing_ids:
                        to_delete = existing_qs.exclude(
                            topic_id__in=provided_existing_ids
                        )
                        if to_delete.exists():
                            to_delete.delete()

                    # To avoid unique order conflicts, compute a safe temp base:
                    current_max = (
                        existing_qs.aggregate(max_order=Max("order"))["max_order"] or 0
                    )
                    temp_base = int(current_max) + len(normalized) + 5

                    # Phase: create/update all mapped topics with unique high orders
                    # (so DB unique on (module, order) will not collide).
                    for idx, it in enumerate(normalized, start=1):
                        temp_order = temp_base + idx
                        t_id = it.get("topicId")
                        if t_id:
                            # update (only if topic belongs to module)
                            try:
                                Topic.objects.filter(
                                    topic_id=t_id, module=module
                                ).update(
                                    title=it["title"],
                                    content=it["content"],
                                    is_active=it["is_active"],
                                    order=temp_order,
                                )
                            except Exception:
                                logger.exception("Failed updating topic %s", t_id)
                        else:
                            # create new topic bound to module
                            try:
                                Topic.objects.create(
                                    module=module,
                                    title=it["title"],
                                    content=it["content"],
                                    order=temp_order,
                                    is_active=it["is_active"],
                                )
                            except Exception:
                                logger.exception(
                                    "Failed creating topic for module %s",
                                    module.module_id,
                                )

                    # Finalize: renumber to contiguous 1..N (TopicService helper)
                    TopicService._renumber_topics(module)

            action = "created" if created else "updated"
            return {
                "success": True,
                "data": cls.to_dict(module, include_topics=True),
                "message": f"Module {action} successfully",
            }

        except Course.DoesNotExist:
            return {"success": False, "data": None, "error": "Course not found"}
        except Exception as e:
            logger.exception(f"Error creating/updating module {module_id}")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def delete_module(cls, module_id):
        """Delete a module"""
        try:
            module = Module.objects.get(module_id=module_id)
            module.delete()
            return {
                "success": True,
                "message": "Module deleted successfully",
                "data": module_id,
            }
        except Module.DoesNotExist:
            return {"success": False, "error": "Module not found"}
        except Exception as e:
            logger.exception(f"Error deleting module {module_id}")
            return {"success": False, "error": str(e)}

    @classmethod
    def duplicate_module(
        cls,
        module_id: str,
        dest_course_id: Optional[str] = None,
        include_topics: bool = True,
    ) -> Dict:
        """
        Duplicate a module. If dest_course_id is provided, duplicate into that course,
        otherwise duplicate into the same course.
        include_topics controls copying of topics.
        """
        try:
            src_module = Module.objects.get(module_id=module_id)

            # determine destination course
            if dest_course_id:
                try:
                    dest_course = Course.objects.get(course_id=dest_course_id)
                except Course.DoesNotExist:
                    return {"success": False, "error": "Destination course not found"}
            else:
                dest_course = src_module.course

            with transaction.atomic():
                # determine order in destination course
                current_max = (
                    Module.objects.filter(course=dest_course).aggregate(
                        max_order=Max("order")
                    )["max_order"]
                    or 0
                )
                new_order = int(current_max) + 1

                duplicated_module = Module.objects.create(
                    course=dest_course,
                    title=f"{src_module.title} (Copy)",
                    content=src_module.content,
                    order=new_order,
                )

                if include_topics:
                    # duplicate topics in the same relative order
                    src_topics = Topic.objects.filter(module=src_module).order_by(
                        "order"
                    )
                    for t_idx, t in enumerate(src_topics, start=1):
                        duplicated = Topic.objects.create(
                            module=duplicated_module,
                            title=t.title,
                            order=t_idx,
                            is_active=t.is_active,
                        )

                        # create new duplicated paragraphs in new topic
                        paragraphs = t.paragraphs.all()

                        print(f"Para graphs under topics: ", paragraphs)
                        if paragraphs:
                            for idx, para in enumerate(paragraphs, start=1):
                                TopicParagraph.objects.create(
                                    topic=duplicated, content=para.content, order=idx
                                )

                    # renumber to be safe
                    TopicService._renumber_topics(duplicated_module)

            return {
                "success": True,
                "data": cls.to_dict(duplicated_module, include_topics=True),
                "message": "Module duplicated successfully",
            }
        except Module.DoesNotExist:
            return {"success": False, "data": None, "error": "Source module not found"}
        except Exception as e:
            logger.exception(f"Error duplicating module {module_id}")
            return {"success": False, "data": None, "error": str(e)}
