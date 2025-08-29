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
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    duration_in_weeks = models.PositiveIntegerField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.course_name
    
class CourseDescription(models.Model):
    description_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey("Course", related_name="descriptions", on_delete=models.CASCADE)
    text = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
        
    
    def save(self, *args, **kwargs):
        if not self.order:
            # find max order for this course
            max_order = (
                CourseDescription.objects.filter(course=self.course).aggregate(models.Max("order"))["order__max"]
            )
            self.order = (max_order or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Description {self.order} for {self.course.course_name}"
    
class CourseDescriptionImage(models.Model):
    image_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.ForeignKey(CourseDescription, related_name="images", on_delete=models.CASCADE)
    image_url = models.TextField()
    s3_key = models.TextField(blank=True, null=True)  
    caption = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.description.description_id}"



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
    correct_answer = models.TextField(
        blank=True, null=True
    )  # TODO: Need to implement this for open in frontend

    def __str__(self):
        return self.question_text


class Topic(models.Model):
    topic_id = models.UUIDField(
    primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    module = models.ForeignKey(
    Module, on_delete=models.CASCADE, related_name="topics")
    title = models.CharField(max_length=255)
    content = models.TextField() 
    order = models.PositiveIntegerField()  
    is_active = models.BooleanField(default=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]  
        unique_together = [("module", "order")] 

    def __str__(self):
        return f"{self.title} (Module: {self.module.title})"

