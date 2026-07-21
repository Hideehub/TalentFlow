from django.conf import settings
from django.db import models

from core.models import BaseModel
from .choices import CANDIDATE_STATUS, EMPLOYMENT_TYPE, INTERVIEW_STATUS, JOB_STATUS


class JobOpening(BaseModel):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="job_openings",
        null=True,
        blank=True,
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

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.title} - {self.department}"


class Candidate(BaseModel):

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="candidates",
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    position_applied_for = models.CharField(max_length=150)
    job = models.ForeignKey(
        JobOpening,
        on_delete=models.SET_NULL,
        related_name="candidates",
        null=True,
        blank=True,
    )
    assigned_recruiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_candidates",
        null=True,
        blank=True,
    )
    years_of_experience = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=CANDIDATE_STATUS,
        default="applied",
    )

    date_applied = models.DateField(auto_now_add=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("company", "email"),
                name="unique_candidate_email_per_company",
            ),
        )

    def __str__(self):
        return self.full_name


class CandidateNote(BaseModel):
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    note = models.TextField()

    def __str__(self):
        return f"Note for {self.candidate.full_name}"


class Interview(BaseModel):
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="interviews",
    )
    title = models.CharField(max_length=150)
    scheduled_at = models.DateTimeField()
    location = models.CharField(max_length=150, blank=True)
    interviewer = models.CharField(max_length=150, blank=True)
    status = models.CharField(
        max_length=20,
        choices=INTERVIEW_STATUS,
        default="scheduled",
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} - {self.candidate.full_name}"
