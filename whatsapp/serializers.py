from rest_framework import serializers

from courses.models import Assessment, Course
from courses.serializers import AssessmentSerializer, CourseSerializer, ModuleSerializer
from .models import (
    AutomationRule,
    UserAssessmentAttempt,
    UserQuestionResponse,
    WhatsappUser,
    UserEnrollment,
)


class UserEnrollmentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    course = CourseSerializer(read_only=True)
    current_module = ModuleSerializer(read_only=True)
    current_assessment_attempt = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = UserEnrollment
        fields = "__all__"


class WhatsappUserSerializer(serializers.ModelSerializer):
    shared_courses_list = CourseSerializer(many=True, read_only=True)
    active_enrollment = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = WhatsappUser
        fields = "__all__"


class UserAssessmentAttemptSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    enrollment = serializers.PrimaryKeyRelatedField(read_only=True)
    assessment = AssessmentSerializer(read_only=True)
    module = ModuleSerializer(read_only=True)

    class Meta:
        model = UserAssessmentAttempt
        fields = "__all__"


class UserAssessmentAttemptWithResponsesSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    enrollment = serializers.PrimaryKeyRelatedField(read_only=True)
    assessment = AssessmentSerializer(read_only=True)
    module = ModuleSerializer(read_only=True)
    responses = serializers.SerializerMethodField()

    class Meta:
        model = UserAssessmentAttempt
        fields = "__all__"

    def get_responses(self, obj):
        questions_responses = UserQuestionResponse.objects.filter(attempt=obj)
        return UserQuestionResponseSerializer(questions_responses, many=True).data


class UserQuestionResponseSerializer(serializers.ModelSerializer):
    attempt = serializers.PrimaryKeyRelatedField(read_only=True)
    question = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = UserQuestionResponse
        fields = "__all__"


class AutomationRuleSerializer(serializers.ModelSerializer):
    daysInactive = serializers.IntegerField(source="days_inactive")
    messageTemplate = serializers.CharField(source="message_template")
    isActive = serializers.BooleanField(source="is_active")

    class Meta:
        model = AutomationRule
        fields = [
            "id",
            "name",
            "daysInactive",
            "messageTemplate",
            "isActive",
            "created_at",
        ]
