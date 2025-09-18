from django.utils import timezone
from django.db import models
from courses.models import (
    Assessment,
    AssessmentQuestion,
    Course,
    Module,
    Topic,
    TopicParagraph,
)
import uuid

# Choices for gender, education, etc.
GENDER_CHOICES = [
    ("male", "Male"),
    ("female", "Female"),
    ("other", "Other"),
    ("prefer-not-to-say", "Prefer not to say"),
]

EDUCATION_LEVEL_CHOICES = [
    ("high-school", "High School"),
    ("undergraduate", "Undergraduate"),
    ("graduate", "Graduate"),
    ("phd", "PhD"),
    ("other", "Other"),
]

ACCOUNT_STATUS_CHOICES = [
    ("active", "Active"),
    ("inactive", "Inactive"),
    ("suspended", "Suspended"),
]

SUBSCRIPTION_TYPE_CHOICES = [
    ("free", "Free"),
    ("premium", "Premium"),
    ("enterprise", "Enterprise"),
]


class WhatsappUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    whatsapp_id = models.CharField(max_length=255, unique=True)
    whatsapp_name = models.CharField(max_length=255)
    registration_date = models.DateTimeField()
    last_active = models.DateTimeField()
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Onboarding tracking
    onboarding_status = models.CharField(
        max_length=20,
        choices=[
            ("not_started", "Not Started"),
            ("started", "Started"),
            ("completed", "Completed"),
            ("restarted", "Restarted"),
        ],
        default="not_started",
    )
    onboarding_step = models.PositiveSmallIntegerField(default=0)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)

    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.IntegerField(default=0)

    # Orientation tracking
    orientation_status = models.CharField(
        max_length=20,
        choices=[
            ("not_started", "Not Started"),
            ("started", "Started"),
            ("completed", "Completed"),
            ("restarted", "Restarted"),
        ],
        default="not_started",
    )
    orientation_step = models.PositiveSmallIntegerField(default=0)
    orientation_completed_at = models.DateTimeField(null=True, blank=True)

    # Post-course enrollment flow tracking
    post_course_status = models.CharField(
        max_length=20,
        choices=[
            ("not_started", "Not Started"),
            ("started", "Started"),
            ("completed", "Completed"),
        ],
        default="not_started",
    )
    post_course_step = models.PositiveSmallIntegerField(default=0)
    post_course_completed_at = models.DateTimeField(null=True, blank=True)

    shared_courses_list = models.ManyToManyField(
        Course, blank=True, related_name="shared_with_users"
    )

    active_enrollment = models.ForeignKey(
        "UserEnrollment",
        on_delete=models.SET_NULL,
        related_name="active_enrollment",
        blank=True,
        null=True,
    )

    age = models.PositiveIntegerField(blank=True, null=True)
    gender = models.CharField(
        max_length=20, choices=GENDER_CHOICES, blank=True, null=True
    )
    education_level = models.CharField(
        max_length=20, choices=EDUCATION_LEVEL_CHOICES, blank=True, null=True
    )
    current_institution = models.CharField(max_length=255, blank=True, null=True)
    interests = models.JSONField(blank=True, null=True)
    timezone = models.CharField(max_length=100, blank=True, null=True)
    preferred_language = models.CharField(max_length=50, blank=True, null=True)

    # Placeholder for foreign key or related models
    # Replace 'UserCourse' and 'TestResult' with actual model names if defined
    # Or use GenericRelation or JSONField if no models exist yet
    enrolled_courses = models.JSONField(blank=True, null=True)
    test_results = models.JSONField(blank=True, null=True)

    message_count = models.PositiveIntegerField(default=0)
    response_rate = models.FloatField(default=0.0)
    completion_rate = models.FloatField(default=0.0)

    account_status = models.CharField(
        max_length=20, choices=ACCOUNT_STATUS_CHOICES, default="active"
    )
    subscription_type = models.CharField(
        max_length=20, choices=SUBSCRIPTION_TYPE_CHOICES, default="free"
    )

    tags = models.JSONField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} ({self.whatsapp_id})"


class UserEnrollment(models.Model):
    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("paused", "Paused"),
    ]
    INTRO_CHOICES = [
        ("not_started", "Not Started"),
        ("delivered", "Delivered"),
        ("delivering", "Delivering"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        WhatsappUser, on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    enrollment_date = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    progress = models.FloatField(default=0.0)  # 0.0 to 1.0 (percentage)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)  # Track completion date
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="in_progress"
    )
    certificate_earned = models.BooleanField(default=False)
    certificate_id = models.CharField(max_length=255, blank=True, null=True)
    certificate_url = models.URLField(
        max_length=500, blank=True, null=True
    )  # Link to PDF in S3

    badge_url = models.URLField(max_length=500, blank=True, null=True)

    introduction = models.CharField(
        max_length=20, choices=INTRO_CHOICES, default="not_started"
    )
    on_intro_step = models.PositiveIntegerField(default=0)

    # Current position tracking
    current_module = models.ForeignKey(
        Module,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_enrollments",
    )
    current_assessment_attempt = models.ForeignKey(
        "UserAssessmentAttempt",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_enrollment",
    )

    conversation_state = models.CharField(
        max_length=50,
        default="idle",  # other states: 'awaiting_user_query', 'offer_quiz_or_content', etc.
        choices=[
            ("idle", "Idle"),
            ("awaiting_user_query", "Awaiting User Query"),
            ("awaiting_continue_confirmation", "Awaiting Continue Confirmation"),
            ("offer_quiz_or_content", "Offer Quiz Or Content"),
            ("in_assessment", "In Assessment"),
            ("course_complete", "Course Complete"),
        ],
    )

    class Meta:
        unique_together = ("user", "course")
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["last_accessed"]),
        ]

    def __str__(self):
        return f"{self.user.whatsapp_id} - {self.course.course_name}"

    def get_level_display(self):
        return "Level {}".format(self.progress)

    @classmethod
    def update_introduction_state(cls, enrollment_id: str, state: str):
        """
        Update the 'introduction' state for a given enrollment.
        Only allows valid INTRO_CHOICES.
        """
        print(
            f"[DEBUG] Requested state update → enrollment_id={enrollment_id}, new_state={state}"
        )

        valid_states = [choice[0] for choice in cls.INTRO_CHOICES]
        print(f"[DEBUG] Valid intro states: {valid_states}")

        if state not in valid_states:
            raise ValueError(f"Invalid state '{state}'. Must be one of {valid_states}")

        try:
            enrollment = cls.objects.get(id=enrollment_id)
            print(
                f"[DEBUG] Found enrollment: {enrollment.id}, current_state={enrollment.introduction}"
            )
        except cls.DoesNotExist:
            raise ValueError(f"Enrollment with id {enrollment_id} not found")

        if enrollment.introduction != state:
            print(
                f"[DEBUG] Updating state from '{enrollment.introduction}' → '{state}'"
            )
            enrollment.introduction = state
            enrollment.save(update_fields=["introduction", "last_accessed"])
            print(
                f"[DEBUG] State updated successfully. New state={enrollment.introduction}"
            )
        else:
            print(f"[DEBUG] No update needed. State already '{state}'")

        return enrollment

    @classmethod
    def increment_intro_step(cls, enrollment_id: str, step: int = 1):
        """
        Safely increments the 'on_intro_step' counter for a given enrollment.
        Default increment is 1.
        """
        try:
            enrollment = cls.objects.get(id=enrollment_id)
        except cls.DoesNotExist:
            raise ValueError(f"Enrollment with id {enrollment_id} not found")

        enrollment.on_intro_step = (enrollment.on_intro_step or 0) + step
        enrollment.last_accessed = timezone.now()
        enrollment.save(update_fields=["on_intro_step", "last_accessed"])

        return enrollment.on_intro_step


class ModuleDeliveryProgress(models.Model):
    STATE_CHOICES = [
        ("not_started", "Not Started"),
        ("content_delivering", "Content Delivering"),
        ("content_delivered", "Content Delivered"),
        ("quiz_delivered", "Quiz Delivered"),
        ("quiz_completed", "Quiz Completed"),
        ("assessment_delivered", "Assessment Delivered"),
        ("assessment_completed", "Assessment Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        UserEnrollment, on_delete=models.CASCADE, related_name="module_progress"
    )
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="delivery_progress"
    )
    current_topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="current_topic",
        default=None,
        null=True,
    )

    state = models.CharField(
        max_length=50, choices=STATE_CHOICES, default="not_started"
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("enrollment", "module")

    def __str__(self):
        return f"{self.enrollment.user} - {self.module} ({self.state})"


class TopicDeliveryProgress(models.Model):
    STATE_CHOICES = [
        ("not_started", "Not Started"),
        ("content_delivering", "Content Delivering"),
        ("content_delivered", "Content Delivered"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        UserEnrollment, on_delete=models.CASCADE, related_name="topic_progress"
    )
    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name="topic_delivery_progress"
    )
    current_paragraph = models.ForeignKey(
        TopicParagraph,
        on_delete=models.CASCADE,
        related_name="current_paragraph",
        default=None,
        null=True,
    )

    state = models.CharField(
        max_length=50, choices=STATE_CHOICES, default="not_started"
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("enrollment", "topic")

    def __str__(self):
        return f"{self.enrollment.user} - {self.topic} ({self.state})"


class UserAssessmentAttempt(models.Model):
    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("abandoned", "Abandoned"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        WhatsappUser, on_delete=models.CASCADE, related_name="assessment_attempts"
    )
    enrollment = models.ForeignKey(
        UserEnrollment, on_delete=models.CASCADE, related_name="assessment_attempts"
    )
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="attempts"
    )
    module = models.ForeignKey(Module, on_delete=models.CASCADE)  # For quick reference
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="in_progress"
    )
    score = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)

    # Progress tracking
    current_question_index = models.PositiveIntegerField(default=0)
    questions_answered = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField()

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["enrollment"]),
        ]

    def __str__(self):
        return f"{self.user.whatsapp_id} - {self.assessment.title}"


class UserQuestionResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        UserAssessmentAttempt, on_delete=models.CASCADE, related_name="responses"
    )
    question = models.ForeignKey(AssessmentQuestion, on_delete=models.CASCADE)

    # Snapshot of question at time of answering
    question_text_snapshot = models.TextField()
    question_type_snapshot = models.CharField(max_length=10)
    options_snapshot = models.JSONField(blank=True, null=True)
    correct_answer_snapshot = models.TextField()

    # User response
    user_answer = models.TextField(blank=True, null=True)
    is_correct = models.BooleanField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["answered_at"]
        indexes = [
            models.Index(fields=["attempt"]),
        ]

    def __str__(self):
        return f"Response to {self.question_text_snapshot[:50]}"


class AutomationRule(models.Model):
    name = models.CharField(max_length=100)
    days_inactive = models.PositiveIntegerField(default=2)  # e.g. 2 days
    message_template = models.TextField()  # WhatsApp message
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class UserMessageLog(models.Model):
    user = models.ForeignKey(WhatsappUser, on_delete=models.CASCADE)
    rule = models.ForeignKey(AutomationRule, on_delete=models.CASCADE)
    message_content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_message_log"
