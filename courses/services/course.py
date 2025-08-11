import logging
from courses.models import Course

logger = logging.getLogger(__name__)


class CourseService:
    @classmethod
    def to_dict(cls, course):
        """Convert Course model instance to dictionary"""
        return {
            "courseId": course.course_id,
            "courseName": course.course_name,
            "description": course.description,
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
            action = "created" if created else "updated"
            return {
                "success": True,
                "data": cls.to_dict(course),
                "message": f"Course {action} successfully",
            }
        except Exception as e:
            logger.exception(f"Error creating/updating course {course_id}")
            return {"success": False, "data": None, "error": str(e)}

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
