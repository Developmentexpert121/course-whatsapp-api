import tempfile
import os
import uuid

import logging
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import MultiPartParser, FormParser
from .services.course import CourseService
from .services.modules import ModuleService
from .services.assesments import AssessmentService
from .services.topics import TopicService
from .serializers import TopicSerializer
from .services.image_service import ImageService
from .models import CourseDescription, CourseDescriptionImage
from rest_framework.parsers import MultiPartParser, FormParser


logger = logging.getLogger(__name__)


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
class CourseDescriptionImageUploadView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, course_id, description_id):
        print(
            f"[INFO] Entered post() | course_id={course_id}, description_id={description_id}"
        )

        # validate description belongs to course
        try:
            desc = CourseDescription.objects.get(
                description_id=description_id, course__course_id=course_id
            )
            print(f"[INFO] Found CourseDescription: {desc}")
        except CourseDescription.DoesNotExist:
            print(
                f"[ERROR] Description not found for course_id={course_id}, description_id={description_id}"
            )
            return Response(
                {"success": False, "error": "Description not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        files = request.FILES.getlist("images") or request.FILES.getlist("image") or []
        print(f"[INFO] Number of files received: {len(files)}")

        created = []

        for f in files:
            try:
                print(
                    f"[INFO] Processing file: {f.name}, size={f.size}, content_type={getattr(f, 'content_type', None)}"
                )

                # Build a deterministic key
                s3_folder = f"images/course_descriptions/{course_id}/{description_id}"
                s3_key = f"{s3_folder}/{uuid.uuid4().hex}_{f.name}"
                print(f"[DEBUG] Generated S3 key: {s3_key}")

                # optionally set content type
                content_type = getattr(f, "content_type", None)

                # Upload via ImageService
                upload_res = ImageService.upload_fileobj_to_s3(
                    f, s3_key, content_type=content_type, acl=None
                )
                print(f"[INFO] Upload response: {upload_res}")

                image_url = upload_res["url"]
                stored_key = upload_res["key"]

                # create DB record
                img = CourseDescriptionImage.objects.create(
                    description=desc,
                    image_url=image_url,
                    s3_key=stored_key,
                    caption=request.POST.get("caption", "") or "",
                )
                print(f"[INFO] Created CourseDescriptionImage: image_id={img.image_id}")

                created.append(
                    {
                        "imageId": str(img.image_id),
                        "imageUrl": image_url,
                        "s3Key": stored_key,
                    }
                )
            except Exception as e:
                print(f"[ERROR] Failed to upload description image: {e}")
                logger.exception("Failed to upload description image: %s", e)
                return Response(
                    {
                        "success": False,
                        "error": "Server error uploading file: " + str(e),
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        print(f"[INFO] Upload process completed | Total uploaded: {len(created)}")
        return Response(
            {"success": True, "data": created}, status=status.HTTP_201_CREATED
        )


@method_decorator(csrf_exempt, name="dispatch")
class CourseDescriptionImageDeleteView(APIView):
    authentication_classes = []
    permission_classes = []

    def delete(self, request, course_id, description_id, image_id):
        try:
            img = CourseDescriptionImage.objects.get(
                image_id=image_id,
                description__description_id=description_id,
                description__course__course_id=course_id,
            )
        except CourseDescriptionImage.DoesNotExist:
            return Response(
                {"success": False, "error": "Image not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Try to delete from S3 if we have s3_key
        if img.s3_key:
            ImageService.delete_from_s3(img.s3_key)

        img.delete()
        return Response(
            {"success": True, "message": "Image deleted"}, status=status.HTTP_200_OK
        )



@method_decorator(csrf_exempt, name="dispatch")
class CourseDescriptionReorderView(APIView):
    
    authentication_classes = []
    permission_classes = []
    def post(self, request, course_id):
        """
        Reorder course descriptions.
        Expected payload: { "descriptions": [ { "descriptionId": "...", "order": 1 }, ... ] }
        """
        descriptions_data = request.data.get("descriptions", [])
        if not descriptions_data:
            return Response(
                {"success": False, "error": "No descriptions provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            for d in descriptions_data:
                desc_id = d.get("descriptionId")
                order = d.get("order")
                if desc_id and order is not None:
                    CourseDescription.objects.filter(
                        course__course_id=course_id, description_id=desc_id
                    ).update(order=order)

            return Response(
                {"success": True, "message": "Descriptions reordered successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
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
        include_topics = request.query_params.get("includeTopics") in (
            "1",
            "true",
            "True",
        )
        if module_id:
            # Get single module
            result = ModuleService.get_module(module_id, include_topics=include_topics)
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


@method_decorator(csrf_exempt, name="dispatch")
class TopicView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, course_id, module_id, topic_id=None):
        if topic_id:
            result = TopicService.get_topic(topic_id)
        else:
            result = TopicService.get_topics_by_module(str(module_id))

        if result.get("success"):
            return Response(
                {
                    "success": True,
                    "message": "Topics fetched successfully",
                    "data": result.get("data"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "error": result.get("error", "Unknown error")},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request, course_id, module_id, topic_id=None):
        data = request.data.copy()

        # Normalize isActive / is_active:
        raw_is_active = None
        if "is_active" in data:
            raw_is_active = data.get("is_active")
        elif "isActive" in data:
            raw_is_active = data.get("isActive")

        if raw_is_active is None:
            # default for creating a topic: active
            is_active_val = True
        else:
            if isinstance(raw_is_active, str):
                is_active_val = raw_is_active.lower() in ("1", "true", "yes")
            else:
                is_active_val = bool(raw_is_active)

        # Normalize order to int if provided
        order_val = None
        if "order" in data and data.get("order") not in (None, ""):
            try:
                order_val = int(data.get("order"))
            except (ValueError, TypeError):
                # invalid order -> ignore and let service compute default
                order_val = None

        payload = {
            "title": data.get("title"),
            "content": data.get("content"),
            # only include order if parsed successfully, else service will compute
        }
        if order_val is not None:
            payload["order"] = order_val

        # always include is_active (coerced boolean)
        payload["is_active"] = is_active_val

        # call service to create the topic
        result = TopicService.create_or_update_topic(
            module_id=str(module_id), topic_id=None, data=payload
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
        return Response(
            {"success": False, "error": result.get("error", "Unknown error")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def put(self, request, course_id, module_id, topic_id):
        data = request.data.copy()

        raw_is_active = None
        if "is_active" in data:
            raw_is_active = data.get("is_active")
        elif "isActive" in data:
            raw_is_active = data.get("isActive")

        is_active_val = None
        if raw_is_active is not None:
            if isinstance(raw_is_active, str):
                is_active_val = raw_is_active.lower() in ("1", "true", "yes")
            else:
                is_active_val = bool(raw_is_active)

        payload = {
            "title": data.get("title"),
            "content": data.get("content"),
            "order": data.get("order"),
        }
        if is_active_val is not None:
            payload["is_active"] = is_active_val

        result = TopicService.create_or_update_topic(
            module_id=str(module_id),
            topic_id=str(topic_id),
            data=payload,
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
        return Response(
            {"success": False, "error": result.get("error", "Unknown error")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, course_id, module_id, topic_id):
        result = TopicService.delete_topic(str(topic_id))
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


@method_decorator(csrf_exempt, name="dispatch")
class TopicReorderView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, course_id, module_id):
        ordered_ids = request.data.get("orderedTopicIds", [])
        result = TopicService.reorder_topics(
            module_id=str(module_id), ordered_topic_ids=ordered_ids
        )
        if result.get("success"):
            return Response(
                {"success": True, "message": result.get("message")},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "error": result.get("error", "Unknown error")},
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(csrf_exempt, name="dispatch")
class CourseDuplicateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, course_id):
        include_modules = request.data.get("includeModules", True)
        include_topics = request.data.get("includeTopics", True)
        result = CourseService.duplicate_course(
            course_id=course_id,
            include_modules=bool(include_modules),
            include_topics=bool(include_topics),
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
        return Response(
            {"success": False, "error": result.get("error", "Unknown error")},
            status=status.HTTP_400_BAD_REQUEST,
        )


@method_decorator(csrf_exempt, name="dispatch")
class ModuleDuplicateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, course_id, module_id):
        include_topics = request.data.get("includeTopics", True)
        # duplicate into same course by default (course_id passed in url) - if you want cross-course, accept destCourseId in body
        result = ModuleService.duplicate_module(
            module_id=module_id,
            dest_course_id=course_id,
            include_topics=bool(include_topics),
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
        return Response(
            {"success": False, "error": result.get("error", "Unknown error")},
            status=status.HTTP_400_BAD_REQUEST,
        )


@method_decorator(csrf_exempt, name="dispatch")
class TopicDuplicateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, course_id, module_id, topic_id):
        # duplicate into same module by default; optionally accept destModuleId in body
        dest_module_id = request.data.get("destModuleId", module_id)
        result = TopicService.duplicate_topic(
            topic_id=topic_id, dest_module_id=dest_module_id
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
        return Response(
            {"success": False, "error": result.get("error", "Unknown error")},
            status=status.HTTP_400_BAD_REQUEST,
        )
