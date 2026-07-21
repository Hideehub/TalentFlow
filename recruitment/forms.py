from django import forms
from django.db.models import Q

from accounts.choices import ROLE_HR_ADMIN, ROLE_RECRUITER
from accounts.decorators import user_has_role
from accounts.tenancy import company_users, get_user_company

from .models import Candidate, CandidateNote, Interview, JobOpening


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = (
            "full_name",
            "email",
            "phone",
            "job",
            "assigned_recruiter",
            "years_of_experience",
            "status",
        )
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "job": forms.Select(attrs={"class": "form-select"}),
            "assigned_recruiter": forms.Select(attrs={"class": "form-select"}),
            "years_of_experience": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        selected_job_id = self.instance.job_id if self.instance and self.instance.pk else None
        jobs = JobOpening.objects.filter(status="open")
        company = get_user_company(self.user)
        if self.user and self.user.is_authenticated and not self.user.is_superuser:
            jobs = jobs.filter(company=company)
        if selected_job_id:
            jobs = JobOpening.objects.filter(Q(status="open") | Q(id=selected_job_id))
            if self.user and self.user.is_authenticated and not self.user.is_superuser:
                jobs = jobs.filter(company=company)
        self.fields["job"].queryset = jobs.order_by("title")
        self.fields["job"].empty_label = "Select an open job"
        self.fields["job"].required = True

        selected_recruiter_id = (
            self.instance.assigned_recruiter_id if self.instance and self.instance.pk else None
        )
        recruiter_filter = Q(groups__name=ROLE_RECRUITER) | Q(is_superuser=True)
        if selected_recruiter_id:
            recruiter_filter |= Q(id=selected_recruiter_id)

        recruiters = company_users(self.user).filter(recruiter_filter).distinct()
        if self.user and self.user.is_authenticated and not (
            self.user.is_superuser or user_has_role(self.user, (ROLE_HR_ADMIN,))
        ):
            recruiters = recruiters.filter(id=self.user.id)
            self.fields["assigned_recruiter"].initial = self.user
            self.fields["assigned_recruiter"].disabled = True

        self.fields["assigned_recruiter"].queryset = recruiters.order_by("first_name", "username")
        self.fields["assigned_recruiter"].empty_label = "Unassigned"


class CandidateStatusForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ("status",)
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class CandidateNoteForm(forms.ModelForm):
    class Meta:
        model = CandidateNote
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
            "interviewer": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["scheduled_at"].input_formats = ["%Y-%m-%dT%H:%M"]


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
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        is_create = self.instance._state.adding
        if is_create:
            self.fields.pop("status")
