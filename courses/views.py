from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .services.course import CourseService
from .services.modules import ModuleService
from .services.assesments import AssessmentService


# Create your views here.
def home(request):
    return HttpResponse(f"Welcome to your courses app.")


@method_decorator(csrf_exempt, name="dispatch")
class CourseView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, course_id=None):
        """Get all courses or a specific course by ID"""
        if course_id:
            result = CourseService.get_course(course_id)
        else:
            result = CourseService.get_all_courses()

        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": "Courses fetched successfully",
                    "data": result.get("data"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                    if "not found" in str(result.get("error")).lower()
                    else status.HTTP_400_BAD_REQUEST
                ),
            )

    def post(self, request):
        """Create or update a course"""
        course_id = request.data.get("courseId")
        # if not course_id:
        #     return Response(
        #         {"success": False, "error": "courseId is required"},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )

        result = CourseService.create_or_update_course(course_id, request.data)
        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": result.get("message"),
                    "data": result.get("data"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def delete(self, request, course_id):
        """Delete a course"""
        result = CourseService.delete_course(course_id)
        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": result.get("message"),
                    "data": result.get("data"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, course_id):
        """Update course status | tags | category"""
        is_active = request.data.get("isActive")
        category = request.data.get("category")
        tags = request.data.get("tags")
        # if is_active is None:
        #     return Response(
        #         {"success": False, "error": "isActive field is required"},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )
        result = None
        if is_active is not None:
            result = CourseService.update_course_status(course_id, is_active)
        if category:
            result = CourseService.update_course_category(course_id, category)
        if tags:
            result = CourseService.update_course_tags(course_id, tags)

        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": result.get("message"),
                    "data": result.get("data"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(csrf_exempt, name="dispatch")
class ModuleView(APIView):
    authentication_classes = []
    permission_classes = []

    # routes:
    # courses/${courses_id}/modules/${module_id} GET will fetch module by id.
    # courses/${courses_id}/modules/             GET will fetch all modules by course id.
    def get(self, request, course_id=None, module_id=None):
        """Get all modules or a specific module by ID"""
        if module_id:
            # Get single module
            result = ModuleService.get_module(module_id)
        else:
            # Get all modules (optionally filtered by course_id)
            result = ModuleService.get_all_modules(course_id)

        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": "Modules fetched successfully",
                    "data": result.get("data"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                    if "not found" in str(result.get("error")).lower()
                    else status.HTTP_400_BAD_REQUEST
                ),
            )

    # routes:
    # courses/${courses_id}/modules/  POST create a new module.
    def post(self, request, course_id=None):
        """Create or update a module - requires course_id"""
        if not course_id:
            return Response(
                {"success": False, "error": "course_id is required in URL"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        module_id = request.data.get("moduleId")
        # if not module_id:
        #     return Response(
        #         {"success": False, "error": "moduleId is required"},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )

        result = ModuleService.create_or_update_module(
            module_id, course_id, request.data
        )
        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": result.get("message"),
                    "data": result.get("data"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    # route:
    # courses/${courses_id}/modules/${module_id}/  DELETE delete a module by id.
    def delete(self, request, module_id, course_id=None):
        """Delete a module"""
        result = ModuleService.delete_module(module_id)
        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": result.get("message"),
                    "data": result.get("data"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(csrf_exempt, name="dispatch")
class AssesmentView(APIView):
    """Assesment View"""

    permission_classes = []
    authentication_classes = []

    # route:
    # /courses/assessment/{assessment_id}
    def get(self, request, assessment_id):
        """Get all assesments in a module"""
        result = AssessmentService.get_assessment_by_id(assessment_id=assessment_id)
        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": result.get("message"),
                    "data": result.get("data"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                }
            )

    # route:
    # /courses/{module_id}/assessment/
    def post(self, request, module_id):
        """Create a new assesment"""
        data = request.data
        if data.get("courseId") is None:
            return Response(
                {"success": False, "error": "Course is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if data.get("moduleId") is None:
            return Response(
                {"success": False, "error": "Module is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = AssessmentService.create_assessment(data)
        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": result.get("message"),
                    "data": result.get("data"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "error": result.get("error", "Unknown error")},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # route:
    # /courses/assessment/{assessment_id}
    def put(self, request, assessment_id):
        """Update an existing assessment"""
        if assessment_id is None:
            return Response({"success": False, "error": "Assessment id is missing"})

        data = request.data
        result = AssessmentService.update_assessment(
            assessment_id=assessment_id, data=data
        )
        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": result.get("message"),
                    "data": result.get("data"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "error": result.get("error", "Unknown error")},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # route:
    # /courses/assessment/{assessment_id}
    def delete(self, request, assessment_id):
        """Delete an existing assessment"""
        if assessment_id is None:
            return Response(
                {"success": False, "error": "Assessment id is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = AssessmentService.delete_assessment(assessment_id=assessment_id)
        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": result.get("message"),
                    "data": assessment_id,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "error": result.get("error", "Unknown error")},
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(csrf_exempt, name="dispatch")
class AssesmentListView(APIView):
    permission_classes = []
    authentication_classes = []

    # route:
    # /courses/modules/{module_id}/assessments-list/
    def get(self, request, module_id):
        """Get assessments by module id"""
        if module_id is None:
            return Response(
                {"success": False, "error": "Module id is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = AssessmentService.get_assessments_by_module_id(module_id=module_id)
        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": result.get("message"),
                    "data": result.get("data"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "error": result.get("error", "Unknown error")},
                status=status.HTTP_200_OK,
            )
