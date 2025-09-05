from rest_framework import serializers
from .models import (
    Course,
    CourseDescription,
    CourseDescriptionImage,
    Module,
    Assessment,
    AssessmentQuestion,
    Topic,
    TopicParagraph,
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


class TopicParagraphSerializer(serializers.ModelSerializer):
    paragraph_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = TopicParagraph
        fields = ["paragraph_id", "content", "order"]


class TopicSerializer(serializers.ModelSerializer):
    topic_id = serializers.UUIDField(read_only=True)
    module_id = serializers.UUIDField(write_only=True, required=True)
    paragraphs = TopicParagraphSerializer(many=True, required=False)

    class Meta:
        model = Topic
        fields = [
            "topic_id",
            "module_id",
            "title",
            "order",
            "is_active",
            "created_at",
            "updated_at",
            "paragraphs",
        ]

    def create(self, validated_data):
        module_id = validated_data.pop("module_id")
        paragraphs_data = validated_data.pop("paragraphs", [])

        # Get module
        try:
            module = Module.objects.get(module_id=module_id)
        except Module.DoesNotExist:
            raise serializers.ValidationError("Module not found")

        # Create topic
        topic = Topic.objects.create(module=module, **validated_data)

        # Create related paragraphs
        for para in paragraphs_data:
            TopicParagraph.objects.create(topic=topic, **para)

        return topic

    def update(self, instance, validated_data):
        if "module_id" in validated_data:
            raise serializers.ValidationError(
                "Cannot change module of an existing topic"
            )

        paragraphs_data = validated_data.pop("paragraphs", None)

        # Update topic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update paragraphs if provided
        if paragraphs_data is not None:
            instance.paragraphs.all().delete()  # 🔥 simple reset
            for para in paragraphs_data:
                TopicParagraph.objects.create(topic=instance, **para)

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
