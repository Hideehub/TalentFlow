from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.choices import DASHBOARD_ROLES, RECRUITMENT_ROLES
from accounts.decorators import role_required

from .choices import CANDIDATE_STATUS, JOB_STATUS
from .forms import (
    CandidateForm,
    CandidateNoteForm,
    CandidateStatusForm,
    InterviewForm,
    JobOpeningForm,
)
from .selectors import (
    candidate_get,
    candidate_interviews,
    candidate_list,
    candidate_notes,
    job_opening_get,
    job_opening_list,
)
from .services import (
    candidate_create,
    candidate_note_create,
    candidate_status_update,
    candidate_update,
    interview_create,
    job_opening_create,
    job_opening_update,
)


@role_required(*RECRUITMENT_ROLES)
def candidate_list_view(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    return render(
        request,
        "recruitment/candidate_list.html",
        {
            "candidates": candidate_list(query=query, status=status, user=request.user),
            "query": query,
            "selected_status": status,
            "candidate_statuses": CANDIDATE_STATUS,
        },
    )


@role_required(*RECRUITMENT_ROLES)
def candidate_create_view(request):
    form = CandidateForm(user=request.user)

    if request.method == "POST":
        candidate, form = candidate_create(data=request.POST, user=request.user)
        if candidate:
            messages.success(request, "Candidate added successfully.")
            return redirect("recruitment:candidate_detail", candidate_id=candidate.id)

    return render(
        request,
        "recruitment/candidate_form.html",
        {"form": form, "title": "Add candidate", "submit_label": "Save candidate"},
    )


@role_required(*RECRUITMENT_ROLES)
def candidate_detail_view(request, candidate_id):
    candidate = candidate_get(candidate_id, user=request.user)
    return render(
        request,
        "recruitment/candidate_detail.html",
        {
            "candidate": candidate,
            "status_form": CandidateStatusForm(instance=candidate),
            "note_form": CandidateNoteForm(),
            "interview_form": InterviewForm(),
            "notes": candidate_notes(candidate),
            "interviews": candidate_interviews(candidate),
        },
    )


@role_required(*RECRUITMENT_ROLES)
def candidate_update_view(request, candidate_id):
    candidate = candidate_get(candidate_id, user=request.user)
    form = CandidateForm(instance=candidate, user=request.user)

    if request.method == "POST":
        updated_candidate, form = candidate_update(
            candidate=candidate,
            data=request.POST,
            user=request.user,
        )
        if updated_candidate:
            messages.success(request, "Candidate updated successfully.")
            return redirect("recruitment:candidate_detail", candidate_id=updated_candidate.id)

    return render(
        request,
        "recruitment/candidate_form.html",
        {"form": form, "title": "Edit candidate", "submit_label": "Update candidate"},
    )


@role_required(*RECRUITMENT_ROLES)
def candidate_status_update_view(request, candidate_id):
    candidate = candidate_get(candidate_id, user=request.user)

    if request.method == "POST":
        updated_candidate, form = candidate_status_update(candidate=candidate, data=request.POST)
        if updated_candidate:
            messages.success(request, "Candidate status updated.")
        else:
            messages.error(request, "Please choose a valid status.")

    return redirect("recruitment:candidate_detail", candidate_id=candidate.id)


@role_required(*RECRUITMENT_ROLES)
def candidate_note_create_view(request, candidate_id):
    candidate = candidate_get(candidate_id, user=request.user)

    if request.method == "POST":
        note, form = candidate_note_create(candidate=candidate, data=request.POST)
        if note:
            messages.success(request, "Note added.")
        else:
            messages.error(request, "Please enter a note.")

    return redirect("recruitment:candidate_detail", candidate_id=candidate.id)


@role_required(*RECRUITMENT_ROLES)
def interview_create_view(request, candidate_id):
    candidate = candidate_get(candidate_id, user=request.user)

    if request.method == "POST":
        interview, form = interview_create(candidate=candidate, data=request.POST)
        if interview:
            messages.success(request, "Interview scheduled.")
        else:
            messages.error(request, "Please check the interview details.")

    return redirect("recruitment:candidate_detail", candidate_id=candidate.id)


@role_required(*DASHBOARD_ROLES)
def job_opening_list_view(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    return render(
        request,
        "recruitment/job_opening_list.html",
        {
            "jobs": job_opening_list(query=query, status=status, user=request.user),
            "query": query,
            "selected_status": status,
            "job_statuses": JOB_STATUS,
        },
    )


@role_required(*DASHBOARD_ROLES)
def job_opening_detail_view(request, job_id):
    return render(
        request,
        "recruitment/job_opening_detail.html",
        {"job": job_opening_get(job_id, user=request.user)},
    )


@role_required(*RECRUITMENT_ROLES)
def job_opening_create_view(request):
    form = JobOpeningForm(user=request.user)

    if request.method == "POST":
        requested_status = request.POST.get("job_status", "open")
        status = "draft" if requested_status == "draft" else "open"
        job, form = job_opening_create(data=request.POST, user=request.user, status=status)
        if job:
            if job.status == "draft":
                messages.success(request, "Draft job saved. You can publish it when it is ready.")
            else:
                messages.success(request, "Job opening created.")
            return redirect("recruitment:job_opening_detail", job_id=job.id)

    return render(
        request,
        "recruitment/job_opening_form.html",
        {
            "form": form,
            "title": "Create job opening",
            "submit_label": "Create job",
            "show_draft_action": True,
        },
    )


@role_required(*RECRUITMENT_ROLES)
def job_opening_update_view(request, job_id):
    job = job_opening_get(job_id, user=request.user)
    form = JobOpeningForm(instance=job, user=request.user)

    if request.method == "POST":
        updated_job, form = job_opening_update(job=job, data=request.POST, user=request.user)
        if updated_job:
            messages.success(request, "Job opening updated.")
            return redirect("recruitment:job_opening_detail", job_id=updated_job.id)

    return render(
        request,
        "recruitment/job_opening_form.html",
        {"form": form, "title": "Edit job opening", "submit_label": "Update job"},
    )
