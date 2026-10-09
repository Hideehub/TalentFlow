from pathlib import Path

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.choices import ROLE_HIRING_MANAGER, ROLE_HR_ADMIN, ROLE_RECRUITER
from accounts.decorators import user_has_role
from accounts.tenancy import get_user_company

from .models import (
    Application,
    ApplicationNote,
    Candidate,
    Interview,
    InterviewFeedback,
    JobOpening,
)

MAX_RESUME_SIZE = 5 * 1024 * 1024
# The first bytes each allowed format must start with, so a renamed file is rejected.
RESUME_SIGNATURES = {
    ".pdf": b"%PDF-",
    ".docx": b"PK\x03\x04",
    ".doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
}


def _company_users(company):
    return get_user_model().objects.filter(profile__company=company)


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = (
            "full_name",
            "email",
            "phone",
            "years_of_experience",
            "source",
        )
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "years_of_experience": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "source": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company", None)
        # On create, an existing email means "reuse that person", so it isn't an error.
        self.allow_existing_email = kwargs.pop("allow_existing_email", False)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if self.allow_existing_email:
            return email
        # company isn't a form field, so model validation skips the DB constraint.
        duplicates = Candidate.objects.filter(company=self.company, email__iexact=email)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("A candidate with this email already exists.")
        return email


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ("job", "assigned_recruiter", "status")
        widgets = {
            "job": forms.Select(attrs={"class": "form-select"}),
            "assigned_recruiter": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.company = kwargs.pop("company", None)
        self.candidate = kwargs.pop("candidate", None)
        super().__init__(*args, **kwargs)

        job_filter = Q(status="open")
        if self.instance.pk and self.instance.job_id:
            job_filter |= Q(id=self.instance.job_id)
        self.fields["job"].queryset = JobOpening.objects.filter(
            job_filter, company=self.company
        ).order_by("title")
        self.fields["job"].empty_label = "Select an open job"
        self.fields["job"].required = True

        recruiter_filter = Q(groups__name=ROLE_RECRUITER) | Q(is_superuser=True)
        if self.instance.pk and self.instance.assigned_recruiter_id:
            recruiter_filter |= Q(id=self.instance.assigned_recruiter_id)

        recruiters = _company_users(self.company).filter(recruiter_filter).distinct()
        if self.user and self.user.is_authenticated and not (
            self.user.is_superuser or user_has_role(self.user, (ROLE_HR_ADMIN,))
        ):
            recruiters = recruiters.filter(id=self.user.id)
            self.fields["assigned_recruiter"].initial = self.user
            self.fields["assigned_recruiter"].disabled = True

        self.fields["assigned_recruiter"].queryset = recruiters.order_by("first_name", "username")
        self.fields["assigned_recruiter"].empty_label = "Unassigned"

    def clean_job(self):
        job = self.cleaned_data["job"]
        if self.candidate and job:
            duplicates = Application.objects.filter(
                candidate=self.candidate, job=job
            ).select_related("assigned_recruiter")
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            duplicate = duplicates.first()
            if duplicate:
                owner = duplicate.assigned_recruiter
                owner_name = (owner.get_full_name() or owner.username) if owner else None
                raise forms.ValidationError(
                    f"Already applied — owned by {owner_name}."
                    if owner_name
                    else "Already applied — unassigned."
                )
        return job


class ApplicationStatusForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ("status",)
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class ApplicationNoteForm(forms.ModelForm):
    class Meta:
        model = ApplicationNote
        fields = ("note",)
        widgets = {
            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Add screening feedback, follow-up items, or context.",
                }
            ),
        }


class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = (
            "title",
            "scheduled_at",
            "location",
            "interviewer",
            "status",
            "notes",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "scheduled_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "interviewer": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)
        self.fields["scheduled_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["interviewer"].queryset = _company_users(self.company).order_by(
            "first_name", "username"
        )
        self.fields["interviewer"].empty_label = "Select an interviewer"


class JobOpeningForm(forms.ModelForm):
    class Meta:
        model = JobOpening
        fields = (
            "title",
            "department",
            "location",
            "employment_type",
            "application_deadline",
            "status",
            "hiring_manager",
            "description",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "employment_type": forms.Select(attrs={"class": "form-select"}),
            "application_deadline": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "hiring_manager": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        is_create = self.instance._state.adding
        if is_create:
            self.fields.pop("status")

        company = get_user_company(self.user) if is_create else self.instance.company
        manager_filter = Q(groups__name=ROLE_HIRING_MANAGER)
        if self.instance.hiring_manager_id:
            manager_filter |= Q(id=self.instance.hiring_manager_id)
        self.fields["hiring_manager"].queryset = (
            _company_users(company).filter(manager_filter).distinct().order_by("first_name", "username")
        )
        self.fields["hiring_manager"].empty_label = "No hiring manager"


class InterviewFeedbackForm(forms.ModelForm):
    class Meta:
        model = InterviewFeedback
        fields = ("recommendation", "comments")
        widgets = {
            "recommendation": forms.Select(attrs={"class": "form-select"}),
            "comments": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }


class ResumeUploadForm(forms.Form):
    resume = forms.FileField(
        help_text="PDF, DOC or DOCX, up to 5 MB.",
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control", "accept": ".pdf,.doc,.docx"}
        ),
    )

    def clean_resume(self):
        resume = self.cleaned_data["resume"]
        extension = Path(resume.name).suffix.lower()
        if extension not in RESUME_SIGNATURES:
            raise forms.ValidationError("Please upload a PDF, DOC or DOCX file.")
        if resume.size > MAX_RESUME_SIZE:
            raise forms.ValidationError("The resume must be 5 MB or smaller.")
        signature = RESUME_SIGNATURES[extension]
        header = resume.read(len(signature))
        resume.seek(0)
        if header != signature:
            raise forms.ValidationError("The file content doesn't match its extension.")
        return resume
