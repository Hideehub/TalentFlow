from django.contrib import admin

from .models import Candidate, CandidateNote, Interview, JobOpening


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "title",
        "department",
        "employment_type",
        "status",
        "application_deadline",
    )
    list_filter = ("company", "status", "employment_type", "department")
    search_fields = ("company__name", "title", "department", "location")
    ordering = ("-created_at",)


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "company",
        "email",
        "phone",
        "job",
        "position_applied_for",
        "assigned_recruiter",
        "status",
        "date_applied",
    )

    search_fields = (
        "full_name",
        "company__name",
        "email",
        "phone",
        "job__title",
        "position_applied_for",
    )

    list_filter = (
        "company",
        "status",
        "job",
        "assigned_recruiter",
        "position_applied_for",
        "date_applied",
    )

    ordering = ("-created_at",)


@admin.register(CandidateNote)
class CandidateNoteAdmin(admin.ModelAdmin):
    list_display = ("candidate", "created_at")
    search_fields = ("candidate__full_name", "candidate__email", "note")
    ordering = ("-created_at",)


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ("candidate", "title", "scheduled_at", "status", "interviewer")
    list_filter = ("status", "scheduled_at")
    search_fields = ("candidate__full_name", "candidate__email", "title", "interviewer")
    ordering = ("scheduled_at",)
