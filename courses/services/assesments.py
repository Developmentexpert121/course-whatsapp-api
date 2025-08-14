import logging
from courses.models import Assessment, AssessmentQuestion
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


class AssessmentService:
    @classmethod
    def to_dict(cls, assessment):
        """Convert Assessment model to dictionary"""
        return {
            "assessmentId": assessment.assessment_id,
            "courseId": assessment.course.course_id if assessment.course else None,
            "moduleId": assessment.module.module_id if assessment.module else None,
            "title": assessment.title,
            "description": assessment.description,
            "questions": [
                {
                    "questionId": q.question_id,
                    "type": q.type,
                    "questionText": q.question_text,
                    "marks": q.marks,
                    "options": q.options if q.type == "mcq" else None,
                }
                for q in assessment.questions.all()
            ],
            "isActive": assessment.is_active,
            "createdAt": assessment.created_at,
            "updatedAt": assessment.updated_at,
            "type": assessment.type,
        }

    @classmethod
    def get_assessment_by_id(cls, assessment_id):
        """Get a single assessment by ID"""
        try:
            assessment = Assessment.objects.get(assessment_id=assessment_id)
            return {
                "success": True,
                "data": cls.to_dict(assessment),
            }
        except ObjectDoesNotExist:
            return {"success": False, "data": None, "error": "Assessment not found"}
        except Exception as e:
            logger.exception("Error retrieving assessment")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def create_assessment(cls, data):
        """Create a new assessment"""
        try:
            assessment = Assessment.objects.create(
                assessment_id=data.get("assessmentId"),
                title=data.get("title"),
                description=data.get("description", ""),
                # questions=data.get("questions", []),
                is_active=data.get("isActive", True),
                type=data.get("type", "assessment"),
                # Note: You'll need to handle course and module relationships here
                course_id=data.get("courseId"),
                module_id=data.get("moduleId"),
            )

            # Save questions
            questions = data.get("questions", [])
            for q in questions:
                AssessmentQuestion.objects.create(
                    assessment=assessment,
                    question_id=q.get("questionId"),
                    type=q.get("type"),
                    question_text=q.get("questionText"),
                    marks=q.get("marks", 0),
                    options=q.get("options") if q.get("type") == "mcq" else None,
                )
            return {
                "success": True,
                "data": cls.to_dict(assessment),
            }
        except Exception as e:
            logger.exception("Error creating assessment")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def update_assessment(cls, assessment_id, data):
        """Update an existing assessment"""
        try:
            assessment = Assessment.objects.get(assessment_id=assessment_id)

            # Field mapping
            field_map = {
                "title": "title",
                "description": "description",
                "isActive": "is_active",
                "type": "type",
                "courseId": "course_id",
                "moduleId": "module_id",
            }

            for input_field, model_field in field_map.items():
                if input_field in data:
                    setattr(assessment, model_field, data[input_field])

            # Handle activation logic
            is_being_activated = data.get("isActive", False)
            assessment_type = data.get("type", assessment.type)
            module_id = data.get("moduleId") or (
                assessment.module.module_id if assessment.module else None
            )

            if is_being_activated:
                # Check if assessment has valid set of questions
                existing_questions = (
                    data.get("questions")
                    if "questions" in data
                    else list(assessment.questions.all())
                )

                if not existing_questions or (len(existing_questions) == 0):
                    return {
                        "success": False,
                        "data": None,
                        "error": "Cannot activate assessment without a question",
                    }

                # Optional: Add more validation rules here (e.g., each MCQ must have options)
                for q in existing_questions:
                    q_type = q.get("type") if isinstance(q, dict) else q.type
                    if q_type == "mcq":
                        options = q.get("options") if isinstance(q, dict) else q.options
                        if not options or len(options) < 2:
                            return {
                                "success": False,
                                "data": None,
                                "error": "Each MCQ must have at least two options",
                            }

                # Deactivate other active assessments of same type/module
                Assessment.objects.filter(
                    module_id=module_id, type=assessment_type
                ).exclude(assessment_id=assessment.assessment_id).update(
                    is_active=False
                )

            assessment.save()

            # Replace questions (if provided)
            if "questions" in data:
                assessment.questions.all().delete()
                for q in data["questions"]:
                    AssessmentQuestion.objects.create(
                        assessment=assessment,
                        question_id=q.get("questionId"),
                        type=q.get("type"),
                        question_text=q.get("questionText"),
                        marks=q.get("marks", 0),
                        options=q.get("options") if q.get("type") == "mcq" else None,
                    )

            return {
                "success": True,
                "data": cls.to_dict(assessment),
                "message": "Assessment updated successfully",
            }

        except ObjectDoesNotExist:
            return {"success": False, "data": None, "error": "Assessment not found"}
        except Exception as e:
            logger.exception("Error updating assessment")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def delete_assessment(cls, assessment_id):
        """Delete an assessment"""
        try:
            assessment = Assessment.objects.get(assessment_id=assessment_id)
            assessment.delete()
            return {"success": True, "data": None}
        except ObjectDoesNotExist:
            return {"success": False, "data": None, "error": "Assessment not found"}
        except Exception as e:
            logger.exception("Error deleting assessment")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def get_assessments_by_module_id(cls, module_id):
        """Get all assessments for a module"""
        try:
            assessments = Assessment.objects.filter(module__module_id=module_id)
            return {
                "success": True,
                "data": [cls.to_dict(assessment) for assessment in assessments],
            }
        except Exception as e:
            logger.exception("Error retrieving assessments by module")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def delete_assessments_by_module_id(cls, module_id):
        """Delete all assessments for a module"""
        try:
            assessments = Assessment.objects.filter(module__module_id=module_id)
            count = assessments.count()
            assessments.delete()
            return {
                "success": True,
                "data": None,
                "message": f"Deleted {count} assessments",
            }
        except Exception as e:
            logger.exception("Error deleting assessments by module")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def update_assessments_by_module_id(cls, module_id, assessments_data):
        """Bulk update assessments for a module"""
        try:
            updated_assessments = []
            for assessment_data in assessments_data:
                assessment_id = assessment_data.get("assessmentId")
                if not assessment_id:
                    continue

                try:
                    assessment = Assessment.objects.get(
                        assessment_id=assessment_id, module__module_id=module_id
                    )
                    for field, value in assessment_data.items():
                        if hasattr(assessment, field):
                            setattr(assessment, field, value)
                    assessment.save()
                    updated_assessments.append(cls.to_dict(assessment))
                except ObjectDoesNotExist:
                    continue

            return {
                "success": True,
                "data": updated_assessments,
            }
        except Exception as e:
            logger.exception("Error bulk updating assessments")
            return {"success": False, "data": None, "error": str(e)}
