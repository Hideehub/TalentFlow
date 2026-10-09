from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from core.models import BaseModel

from .choices import (
    APPLICATION_STATUS,
    CANDIDATE_SOURCE,
    EMPLOYMENT_TYPE,
    INTERVIEW_STATUS,
    JOB_STATUS,
)


class JobOpening(BaseModel):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="job_openings",
    )
    title = models.CharField(max_length=150)
    department = models.CharField(max_length=100)
    location = models.CharField(max_length=150, blank=True)
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE,
        default="full_time",
    )
    description = models.TextField(blank=True)
    application_deadline = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=JOB_STATUS,
        default="open",
    )
    hiring_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="managed_job_openings",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.title} - {self.department}"


class Candidate(BaseModel):
    """The person. What they applied for lives on Application."""

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="candidates",
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    years_of_experience = models.PositiveIntegerField(default=0)
    source = models.CharField(
        max_length=20,
        choices=CANDIDATE_SOURCE,
        default="other",
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                Lower("email"),
                "company",
                name="unique_candidate_email_ci_per_company",
            ),
        )

    def __str__(self):
        return self.full_name


class Application(BaseModel):
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    job = models.ForeignKey(
        JobOpening,
        on_delete=models.SET_NULL,
        related_name="applications",
        null=True,
        blank=True,
    )
    # Only set when an import row had no matching open job.
    imported_position = models.CharField(max_length=150, blank=True)
    status = models.CharField(
        max_length=20,
        choices=APPLICATION_STATUS,
        default="applied",
    )
    assigned_recruiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_applications",
        null=True,
        blank=True,
    )
    date_applied = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = (
            models.UniqueConstraint(
                fields=("candidate", "job"),
                name="unique_application_per_candidate_job",
            ),
            # Postgres treats NULL jobs as distinct, so job-less (imported) applications
            # need their own rule: one per candidate per position text.
            models.UniqueConstraint(
                "candidate",
                Lower("imported_position"),
                condition=Q(job__isnull=True),
                name="unique_imported_application_per_candidate_position",
            ),
        )

    def __str__(self):
        return f"{self.candidate} - {self.position}"

    @property
    def position(self):
        return self.job.title if self.job else self.imported_position


class ApplicationNote(BaseModel):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="application_notes",
        null=True,
    )
    note = models.TextField()

    def __str__(self):
        return f"Note for {self.application}"


class Interview(BaseModel):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="interviews",
    )
    title = models.CharField(max_length=150)
    scheduled_at = models.DateTimeField()
    location = models.CharField(max_length=150, blank=True)
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="interviews",
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=INTERVIEW_STATUS,
        default="scheduled",
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} - {self.application.candidate.full_name}"
