import logging
from typing import Dict
import uuid
from courses.models import Course, CourseDescription, CourseDescriptionImage
from django.db import transaction
from courses.services.modules import ModuleService
from django.db.models import Max
from ..models import CourseDescription, CourseDescriptionImage

logger = logging.getLogger(__name__)

class CourseService:
    @classmethod
    def to_dict(cls, course):
        """Convert Course model instance to dictionary"""
        descriptions = []
        for d in course.descriptions.order_by("order").all():
            images = []
            for img in d.images.all():
                images.append(
                    {
                        "imageId": str(img.image_id),
                        "imageUrl": img.image_url,
                        "caption": img.caption,
                        "createdAt": img.created_at,
                    }
                )

            descriptions.append(
                {
                    "descriptionId": str(d.description_id),
                    "text": d.text,
                    "order": d.order,
                    "createdAt": d.created_at,
                    "updatedAt": d.updated_at,
                    "images": images,
                }
            )

        return {
            "courseId": course.course_id,
            "courseName": course.course_name,
            "description": course.description,
            "descriptions": descriptions,
            "category": course.category,
            "createdAt": course.created_at,
            "updatedAt": course.updated_at,
            "durationInWeeks": course.duration_in_weeks,
            "level": course.level,
            "tags": course.tags,
            "isActive": course.is_active,
        }

    @classmethod
    def get_all_courses(cls):
        """Retrieve all courses"""
        try:
            courses = Course.objects.all()
            return {
                "success": True,
                "data": [cls.to_dict(course) for course in courses],
            }
        except Exception as e:
            logger.exception("Error retrieving courses")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def get_course(cls, course_id):
        """Retrieve a course by ID"""
        try:
            course = Course.objects.get(course_id=course_id)
            return {"success": True, "data": cls.to_dict(course)}
        except Course.DoesNotExist:
            return {"success": False, "data": None, "error": "Course not found"}
        except Exception as e:
            logger.exception(f"Error retrieving course {course_id}")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def create_or_update_course(cls, course_id, data):
        """Create or update a course"""
        try:
            course, created = Course.objects.update_or_create(
                course_id=course_id,
                defaults={
                    "course_name": data.get("courseName"),
                    "description": data.get("description"),
                    "category": data.get("category"),
                    "duration_in_weeks": data.get("durationInWeeks"),
                    "level": data.get("level"),
                    "tags": data.get("tags", []),
                    "is_active": data.get("isActive", True),
                    
                },
            )
                # Process descriptions if provided
            incoming = data.get("descriptions", None)
            if incoming is not None:
                    # Map existing descriptions by id for quick lookup
                    existing = {str(d.description_id): d for d in course.descriptions.all()}
                    kept_ids = []

                    for idx, d in enumerate(incoming):
                        desc_id = d.get("descriptionId")
                        text = d.get("text", "")
                        order = d.get("order", idx + 1)

                        if desc_id:
                            # update existing if present
                            existing_obj = existing.get(str(desc_id))
                            if existing_obj:
                                existing_obj.text = text
                                existing_obj.order = order
                                existing_obj.save()
                                kept_ids.append(str(existing_obj.description_id))
                            else:
                                # incoming id doesn't match any existing -> create new
                                newd = CourseDescription.objects.create(course=course, text=text, order=order)
                                kept_ids.append(str(newd.description_id))
                        else:
                            # create new description
                            newd = CourseDescription.objects.create(course=course, text=text, order=order)
                            kept_ids.append(str(newd.description_id))

                    # delete descriptions that were removed from incoming
                    if kept_ids:
                        course.descriptions.exclude(description_id__in=kept_ids).delete()
                    else:
                        # empty list incoming -> remove all
                        course.descriptions.all().delete()

            action = "created" if created else "updated"
            return {
                "success": True,
                "data": cls.to_dict(course),
                "message": f"Course {action} successfully",
            }

        except Exception as e:
            logger.exception(f"Error creating/updating course {course_id}: {e}")
            return {"success": False, "data": None, "error": str(e)}


    @classmethod
    def _renumber_descriptions(cls, course):
        from courses.models import CourseDescription
        descriptions = CourseDescription.objects.filter(course=course).order_by("order")
        for order, desc in enumerate(descriptions, start=1):
            if desc.order != order:
                desc.order = order
                desc.save()



    @classmethod
    def delete_course(cls, course_id):
        """Delete a course"""
        try:
            course = Course.objects.get(course_id=course_id)
            course.delete()
            return {
                "success": True,
                "message": "Course deleted successfully",
                "data": course_id,
            }
        except Course.DoesNotExist:
            return {"success": False, "error": "Course not found"}
        except Exception as e:
            logger.exception(f"Error deleting course {course_id}")
            return {"success": False, "error": str(e)}

    @classmethod
    def update_course_status(cls, course_id, is_active):
        """Update course status with activation validation"""
        try:
            course = Course.objects.get(course_id=course_id)

            if is_active:
                # --- Rule 1: Must have at least one module ---
                modules = course.modules.all()
                if not modules.exists():
                    return {
                        "success": False,
                        "error": "Cannot activate course: At least one module is required.",
                    }

                # --- Rule 2: Each module must have one active assessment and one active quiz ---
                pending_modules = []

                for module in modules:
                    missing_items = []

                    if not module.assessments.filter(
                        is_active=True, type="assessment"
                    ).exists():
                        missing_items.append("active assessment")

                    if not module.assessments.filter(
                        is_active=True, type="quiz"
                    ).exists():
                        missing_items.append("active quiz")

                    if missing_items:
                        pending_modules.append(
                            f"Module '{module.title}' is missing: {', '.join(missing_items)}"
                        )

                if pending_modules:
                    return {
                        "success": False,
                        "error": "Cannot activate course due to the following issues:\n"
                        + "\n".join(pending_modules),
                    }

            # If all validations pass or course is being deactivated
            course.is_active = is_active
            course.save()

            return {
                "success": True,
                "data": cls.to_dict(course),
                "message": "Course status updated successfully",
            }

        except Course.DoesNotExist:
            return {"success": False, "error": "Course not found"}
        except Exception as e:
            logger.exception(f"Error updating status for course {course_id}")
            return {"success": False, "error": str(e)}

    @classmethod
    def update_course_category(cls, course_id, category):
        """Update course category"""
        try:
            course = Course.objects.get(course_id=course_id)
            course.category = category
            course.save()
            return {
                "success": True,
                "data": cls.to_dict(course),
                "message": "Course category updated successfully",
            }
        except Course.DoesNotExist:
            return {"success": False, "error": "Course not found"}
        except Exception as e:
            logger.exception(f"Error updating status for course {course_id}")
            return {"success": False, "error": str(e)}

    @classmethod
    def update_course_tags(cls, course_id, tags):
        """Update course status"""
        try:
            course = Course.objects.get(course_id=course_id)
            course.tags = tags
            course.save()
            return {
                "success": True,
                "data": cls.to_dict(course),
                "message": "Course tags updated successfully",
            }
        except Course.DoesNotExist:
            return {"success": False, "error": "Course not found"}
        except Exception as e:
            logger.exception(f"Error updating status for course {course_id}")
            return {"success": False, "error": str(e)}
        
    @classmethod
    def duplicate_course(cls, course_id: str, include_modules: bool = True, include_topics: bool = True) -> Dict:
        """
        Duplicate a course. include_modules controls whether to copy modules,
        include_topics controls whether modules should include topics.
        """
        try:
            src_course = Course.objects.get(course_id=course_id)

            with transaction.atomic():
                # create new course
                duplicated_course = Course.objects.create(
                    course_name=f"{src_course.course_name} (Copy)",
                    description=src_course.description,
                    category=src_course.category,
                    duration_in_weeks=src_course.duration_in_weeks,
                    level=src_course.level,
                    tags=src_course.tags,
                    is_active=False,  # duplicates start inactive by default
                )

                if include_modules:
                    src_modules = src_course.modules.order_by("order")
                    for mod in src_modules:
                        # call module duplication, duplicating topics depends on include_topics
                        ModuleService.duplicate_module(
                            module_id=str(mod.module_id),
                            dest_course_id=str(duplicated_course.course_id),
                            include_topics=include_topics,
                        )

            return {"success": True, "data": cls.to_dict(duplicated_course), "message": "Course duplicated successfully"}
        except Course.DoesNotExist:
            return {"success": False, "data": None, "error": "Source course not found"}
        except Exception as e:
            logger.exception(f"Error duplicating course {course_id}")
            return {"success": False, "data": None, "error": str(e)}

