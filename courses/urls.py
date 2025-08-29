from django.urls import path
from .views import CourseDescriptionReorderView, CourseDuplicateView, CourseView, ModuleDuplicateView, ModuleView, AssesmentView, AssesmentListView, TopicDuplicateView, TopicReorderView, TopicView, home, CourseDescriptionImageUploadView, CourseDescriptionImageDeleteView

# prefixed by courses/
urlpatterns = [
    path("", CourseView.as_view(), name="courses"),
    path("<str:course_id>", CourseView.as_view(), name="course-detail"),
    path("<str:course_id>/modules/", ModuleView.as_view(), name="course-modules"),
    path(
        "<str:course_id>/modules/<str:module_id>",
        ModuleView.as_view(),
        name="module-detail",
    ),
    path(
        "assessment/<str:assessment_id>/",
        AssesmentView.as_view(),
        name="assessment-detail",
    ),
    path(
        "modules/<str:module_id>/assessment/",
        AssesmentView.as_view(),
        name="assessment-create",
    ),
    path(
        "modules/<str:module_id>/assessments-list/",
        AssesmentListView.as_view(),
        name="assessment-list-get",
    ),
    path(
    "<str:course_id>/modules/<str:module_id>/topics/",
    TopicView.as_view(),
    name="topic-list-create",
    ),
    path(
    "<str:course_id>/modules/<str:module_id>/topics/reorder/",
    TopicReorderView.as_view(),
    name="topic-reorder",
    ),

    path(
    "<str:course_id>/modules/<str:module_id>/topics/<str:topic_id>/",
    TopicView.as_view(),
    name="topic-detail",
    ),
    path("<str:course_id>/duplicate/", CourseDuplicateView.as_view(), name="course-duplicate"),
    path("<str:course_id>/modules/<str:module_id>/duplicate/", ModuleDuplicateView.as_view(), name="module-duplicate"),
    path("<str:course_id>/modules/<str:module_id>/topics/<str:topic_id>/duplicate/", TopicDuplicateView.as_view(), name="topic-duplicate"),
    path("<str:course_id>/descriptions/<str:description_id>/images/", CourseDescriptionImageUploadView.as_view(), name="course-description-images"),
    path("<str:course_id>/descriptions/<str:description_id>/images/<str:image_id>/", CourseDescriptionImageDeleteView.as_view(), name="description-image-delete"),
    path("<str:course_id>/descriptions/reorder/", CourseDescriptionReorderView.as_view(), name="course-description-reorder",
    ),
]
