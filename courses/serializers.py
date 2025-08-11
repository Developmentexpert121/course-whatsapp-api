from rest_framework import serializers
from .models import Course, Module, Assessment, AssessmentQuestion


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            "course_id",
            "course_name",
            "description",
            "category",
            "created_at",
            "updated_at",
            "duration_in_weeks",
            "level",
            "tags",
            "is_active",
        ]


class ModuleSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Module
        fields = [
            "module_id",
            "course",
            "title",
            "content",
            "order",
            "created_at",
            "updated_at",
        ]


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentQuestion
        fields = [
            "question_id",
            "assessment",
            "type",
            "question_text",
            "marks",
            "options",
            "correct_answer",
        ]


class AssessmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    module = ModuleSerializer(read_only=True)
    questions = AssessmentQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Assessment
        fields = [
            "assessment_id",
            "course",
            "module",
            "title",
            "description",
            "is_active",
            "created_at",
            "updated_at",
            "type",
            "questions",
        ]
