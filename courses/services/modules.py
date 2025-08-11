import logging
from courses.models import Course, Module

logger = logging.getLogger(__name__)


class ModuleService:
    @classmethod
    def to_dict(cls, module):
        """Convert Module model instance to dictionary"""
        return {
            "moduleId": module.module_id,
            "courseId": module.course.course_id,
            "title": module.title,
            "content": module.content,
            "order": module.order,
            "createdAt": module.created_at,
            "updatedAt": module.updated_at,
        }

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
    def get_module(cls, module_id):
        """Retrieve a module by ID"""
        try:
            module = Module.objects.get(module_id=module_id)
            return {"success": True, "data": cls.to_dict(module)}
        except Module.DoesNotExist:
            return {"success": False, "data": None, "error": "Module not found"}
        except Exception as e:
            logger.exception(f"Error retrieving module {module_id}")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def create_or_update_module(cls, module_id, course_id, data):
        """Create or update a module"""
        try:
            # First get the course instance
            course = Course.objects.get(course_id=course_id)

            module, created = Module.objects.update_or_create(
                module_id=module_id,
                defaults={
                    "course": course,
                    "title": data.get("title"),
                    "content": data.get("content"),
                    "order": data.get("order", 0),
                },
            )
            action = "created" if created else "updated"
            return {
                "success": True,
                "data": cls.to_dict(module),
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
