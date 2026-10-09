from pathlib import Path

from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.choices import ROLE_RECRUITER
from accounts.decorators import user_has_role
from accounts.tenancy import get_user_company

from .forms import (
    ApplicationForm,
    ApplicationNoteForm,
    ApplicationStatusForm,
    CandidateForm,
    InterviewFeedbackForm,
    InterviewForm,
    JobOpeningForm,
    ResumeUploadForm,
)
from .models import ApplicationStatusChange, Candidate

APPLICATION_PREFIX = "application"
CANDIDATE_JUST_ADDED = (
    "Someone just added a candidate with this email. "
    "Submit again to add this application to their profile."
)


def _find_candidate(company, email):
    if not email:
        return None
    return Candidate.objects.filter(company=company, email__iexact=email).first()


def record_status_change(application, *, from_status, user=None):
    """Log a status move. Every service that changes status goes through here."""
    if application.status == from_status:
        return None
    return ApplicationStatusChange.objects.create(
        application=application,
        from_status=from_status,
        to_status=application.status,
        changed_by=user if user and user.is_authenticated else None,
    )


def _assign_creating_recruiter(application, user):
    if user and not application.assigned_recruiter and user_has_role(user, (ROLE_RECRUITER,)):
        application.assigned_recruiter = user


@transaction.atomic
def candidate_create(*, data, user=None):
    """Create an application, and the person too unless their email already exists.

    Returns (candidate, created, candidate_form, application_form). An existing person's
    details are kept as they are; only the new application is added.
    """
    company = get_user_company(user)
    email = (data.get("email") or "").strip()
    existing = _find_candidate(company, email)
    candidate_form = CandidateForm(data=data, company=company, allow_existing_email=True)
    # Passing the existing person lets the form reject a second application to the same job.
    application_form = ApplicationForm(
        data=data, user=user, company=company, candidate=existing, prefix=APPLICATION_PREFIX
    )
    if candidate_form.is_valid() and application_form.is_valid():
        candidate = existing
        if candidate is None:
            candidate = candidate_form.save(commit=False)
            candidate.company = company
            # Another request can create the same email between the lookup and this insert.
            # The savepoint keeps the outer transaction usable after the IntegrityError.
            try:
                with transaction.atomic():
                    candidate.save()
            except IntegrityError:
                candidate_form.add_error("email", CANDIDATE_JUST_ADDED)
                return None, False, candidate_form, application_form

        application = application_form.save(commit=False)
        application.candidate = candidate
        _assign_creating_recruiter(application, user)
        application.save()
        record_status_change(application, from_status="", user=user)
        return candidate, existing is None, candidate_form, application_form
    return None, False, candidate_form, application_form


@transaction.atomic
def candidate_update(*, candidate, data):
    form = CandidateForm(data=data, instance=candidate, company=candidate.company)
    if form.is_valid():
        return form.save(), form
    return None, form


@transaction.atomic
def application_create(*, candidate, data, user=None):
    form = ApplicationForm(
        data=data, user=user, company=candidate.company, candidate=candidate
    )
    if form.is_valid():
        application = form.save(commit=False)
        application.candidate = candidate
        _assign_creating_recruiter(application, user)
        application.save()
        record_status_change(application, from_status="", user=user)
        return application, form
    return None, form


@transaction.atomic
def application_update(*, application, data, user=None):
    # Read before validation: is_valid() writes the posted values onto the instance.
    from_status = application.status
    form = ApplicationForm(
        data=data,
        instance=application,
        user=user,
        company=application.candidate.company,
        candidate=application.candidate,
    )
    if form.is_valid():
        application = form.save()
        record_status_change(application, from_status=from_status, user=user)
        return application, form
    return None, form


@transaction.atomic
def application_status_update(*, application, data, user=None):
    from_status = application.status
    form = ApplicationStatusForm(data=data, instance=application)
    if form.is_valid():
        application = form.save()
        record_status_change(application, from_status=from_status, user=user)
        return application, form
    return None, form


@transaction.atomic
def application_note_create(*, application, data, author=None):
    form = ApplicationNoteForm(data=data)
    if form.is_valid():
        note = form.save(commit=False)
        note.application = application
        note.author = author
        note.save()
        return note, form
    return None, form


@transaction.atomic
def interview_create(*, application, data):
    form = InterviewForm(data=data, company=application.candidate.company)
    if form.is_valid():
        interview = form.save(commit=False)
        interview.application = application
        interview.save()
        return interview, form
    return None, form


@transaction.atomic
def job_opening_create(*, data, user=None, status="open"):
    form = JobOpeningForm(data=data, user=user)
    if form.is_valid():
        job = form.save(commit=False)
        job.company = get_user_company(user)
        job.status = status
        job.save()
        form.save_m2m()
        return job, form
    return None, form


@transaction.atomic
def job_opening_update(*, job, data, user=None):
    form = JobOpeningForm(data=data, instance=job, user=user)
    if form.is_valid():
        return form.save(), form
    return None, form


@transaction.atomic
def interview_feedback_submit(*, interview, data, user):
    """Create the interviewer's feedback, or update it if they already gave some."""
    existing = getattr(interview, "feedback", None)
    form = InterviewFeedbackForm(data=data, instance=existing)
    if form.is_valid():
        feedback = form.save(commit=False)
        feedback.interview = interview
        feedback.author = user
        feedback.save()
        return feedback, form
    return None, form


@transaction.atomic
def candidate_resume_upload(*, candidate, data, files):
    form = ResumeUploadForm(data=data, files=files)
    if form.is_valid():
        uploaded = form.cleaned_data["resume"]
        old_storage, old_name = candidate.resume.storage, candidate.resume.name
        candidate.resume = uploaded
        candidate.resume_original_name = Path(uploaded.name).name[:255]
        candidate.resume_uploaded_at = timezone.now()
        candidate.save(update_fields=["resume", "resume_original_name", "resume_uploaded_at", "updated_at"])
        if old_name:
            # Delete the replaced file only once the new one is committed.
            transaction.on_commit(lambda: old_storage.delete(old_name))
        return candidate, form
    return None, form
