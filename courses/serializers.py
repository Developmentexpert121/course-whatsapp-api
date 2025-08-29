from rest_framework import serializers
from .models import (
    Course,
    CourseDescription,
    CourseDescriptionImage,
    Module,
    Assessment,
    AssessmentQuestion,
    Topic,
)


class CourseDescriptionImageSerializer(serializers.ModelSerializer):
    imageId = serializers.UUIDField(source="image_id", read_only=True)
    imageUrl = serializers.CharField(source="image_url", read_only=True)
    caption = serializers.CharField(read_only=True)

    class Meta:
        model = CourseDescriptionImage
        fields = ("imageId", "imageUrl", "caption", "created_at")


class CourseDescriptionSerializer(serializers.ModelSerializer):
    descriptionId = serializers.UUIDField(source="description_id", read_only=True)
    images = CourseDescriptionImageSerializer(many=True, read_only=True)
    text = serializers.CharField()
    order = serializers.IntegerField()

    class Meta:
        model = CourseDescription
        fields = (
            "descriptionId",
            "text",
            "order",
            "images",
            "created_at",
            "updated_at",
        )


class CourseSerializer(serializers.ModelSerializer):
    descriptions = CourseDescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            "course_id",
            "course_name",
            "description",
            "descriptions",
            "category",
            "created_at",
            "updated_at",
            "duration_in_weeks",
            "level",
            "tags",
            "is_active",
            "descriptions",
        ]


class CourseDescriptionImageSerializer(serializers.ModelSerializer):
    imageId = serializers.UUIDField(source="image_id", read_only=True)
    imageUrl = serializers.CharField(source="image_url", read_only=True)
    caption = serializers.CharField(read_only=True)

    class Meta:
        model = CourseDescriptionImage
        fields = ["imageId", "imageUrl", "caption", "created_at"]


class TopicSerializer(serializers.ModelSerializer):
    topic_id = serializers.UUIDField(read_only=True)
    module_id = serializers.UUIDField(write_only=True, required=True)

    class Meta:
        model = Topic
        fields = [
            "topic_id",
            "module_id",
            "title",
            "content",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        # Extract module_id from validated_data
        module_id = validated_data.pop("module_id")

        # Get the module instance
        try:
            module = Module.objects.get(module_id=module_id)
        except Module.DoesNotExist:
            raise serializers.ValidationError("Module not found")

        # Create the topic
        topic = Topic.objects.create(module=module, **validated_data)
        return topic

    def update(self, instance, validated_data):
        # If module_id is provided in update, it's not allowed
        if "module_id" in validated_data:
            raise serializers.ValidationError(
                "Cannot change module of an existing topic"
            )

        # Update the topic instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ModuleSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    topics = TopicSerializer(many=True, read_only=True)

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
            "topics",
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
