from django.urls import path
from .views import CourseView, ModuleView, AssesmentView, AssesmentListView, home

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
]
