from django.contrib import admin

from .models import (
    Application,
    ApplicationNote,
    ApplicationStatusChange,
    Candidate,
    Interview,
    InterviewFeedback,
    JobOpening,
)


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "title",
        "department",
        "employment_type",
        "status",
        "hiring_manager",
        "application_deadline",
    )
    list_filter = ("company", "status", "employment_type", "department")
    search_fields = ("company__name", "title", "department", "location")
    ordering = ("-created_at",)


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("full_name", "company", "email", "phone", "source", "created_at")
    search_fields = ("full_name", "company__name", "email", "phone")
    list_filter = ("company", "source")
    ordering = ("-created_at",)
    # Resumes are uploaded and served only through the app's validated, scoped views.
    exclude = ("resume", "resume_original_name", "resume_uploaded_at")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "job",
        "imported_position",
        "assigned_recruiter",
        "status",
        "date_applied",
    )
    search_fields = (
        "candidate__full_name",
        "candidate__email",
        "candidate__company__name",
        "job__title",
        "imported_position",
    )
    list_filter = ("candidate__company", "status", "job", "assigned_recruiter", "date_applied")
    ordering = ("-created_at",)


@admin.register(ApplicationNote)
class ApplicationNoteAdmin(admin.ModelAdmin):
    list_display = ("application", "author", "created_at")
    search_fields = ("application__candidate__full_name", "application__candidate__email", "note")
    ordering = ("-created_at",)


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ("application", "title", "scheduled_at", "status", "interviewer")
    list_filter = ("status", "scheduled_at")
    search_fields = (
        "application__candidate__full_name",
        "application__candidate__email",
        "title",
        "interviewer__username",
    )
    ordering = ("scheduled_at",)


@admin.register(ApplicationStatusChange)
class ApplicationStatusChangeAdmin(admin.ModelAdmin):
    list_display = ("application", "from_status", "to_status", "changed_by", "created_at")
    list_filter = ("to_status",)
    ordering = ("-created_at",)


@admin.register(InterviewFeedback)
class InterviewFeedbackAdmin(admin.ModelAdmin):
    list_display = ("interview", "author", "recommendation", "created_at")
    list_filter = ("recommendation",)
    ordering = ("-created_at",)
