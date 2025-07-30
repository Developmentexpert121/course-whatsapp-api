import uuid
from django.db import models


class Course(models.Model):
    LEVEL_CHOICES = [
        ("Beginner", "Beginner"),
        ("Intermediate", "Intermediate"),
        ("Advanced", "Advanced"),
    ]

    course_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    course_name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    duration_in_weeks = models.PositiveIntegerField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.course_name


class Module(models.Model):
    module_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=100)
    content = models.TextField()
    order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]  # Ensures modules are ordered by their order field

    def __str__(self):
        return f"{self.title} (Course: {self.course.course_name})"


class Assessment(models.Model):
    ASSESSMENT_TYPE_CHOICES = [
        ("assessment", "Assessment"),
        ("quiz", "Quiz"),
    ]

    assessment_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="assessments",
        null=True,
        blank=True,
    )
    module = models.ForeignKey(
        "courses.Module",
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    type = models.CharField(
        max_length=10, choices=ASSESSMENT_TYPE_CHOICES, default="assessment"
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Assessment"
        verbose_name_plural = "Assessments"

    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"


class AssessmentQuestion(models.Model):
    QUESTION_TYPE_CHOICES = [
        ("mcq", "Multiple Choice"),
        ("open", "Open Ended"),
    ]

    question_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        "courses.Assessment", on_delete=models.CASCADE, related_name="questions"
    )
    type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES)
    question_text = models.TextField()
    marks = models.FloatField()
    options = models.JSONField(blank=True, null=True)  # Only for MCQ type

    def __str__(self):
        return self.question_text
