from django.db import transaction

from accounts.choices import ROLE_RECRUITER
from accounts.decorators import user_has_role
from accounts.tenancy import get_user_company

from .forms import (
    CandidateForm,
    CandidateNoteForm,
    CandidateStatusForm,
    InterviewForm,
    JobOpeningForm,
)


@transaction.atomic
def candidate_create(*, data, user=None):
    form = CandidateForm(data=data, user=user)
    if form.is_valid():
        candidate = form.save(commit=False)
        candidate.company = candidate.job.company or get_user_company(user)
        candidate.position_applied_for = candidate.job.title
        if user and not candidate.assigned_recruiter and user_has_role(user, (ROLE_RECRUITER,)):
            candidate.assigned_recruiter = user
        candidate.save()
        return candidate, form
    return None, form


@transaction.atomic
def candidate_update(*, candidate, data, user=None):
    form = CandidateForm(data=data, instance=candidate, user=user)
    if form.is_valid():
        candidate = form.save(commit=False)
        candidate.company = candidate.job.company or candidate.company or get_user_company(user)
        candidate.position_applied_for = candidate.job.title
        candidate.save()
        return candidate, form
    return None, form


@transaction.atomic
def candidate_status_update(*, candidate, data):
    form = CandidateStatusForm(data=data, instance=candidate)
    if form.is_valid():
        return form.save(), form
    return None, form


@transaction.atomic
def candidate_note_create(*, candidate, data):
    form = CandidateNoteForm(data=data)
    if form.is_valid():
        note = form.save(commit=False)
        note.candidate = candidate
        note.save()
        return note, form
    return None, form


@transaction.atomic
def interview_create(*, candidate, data):
    form = InterviewForm(data=data)
    if form.is_valid():
        interview = form.save(commit=False)
        interview.candidate = candidate
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
        updated_job = form.save()
        updated_job.candidates.update(position_applied_for=updated_job.title)
        return updated_job, form
    return None, form
