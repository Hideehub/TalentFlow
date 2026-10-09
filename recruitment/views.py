from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.choices import DASHBOARD_ROLES, RECRUITMENT_ROLES
from accounts.decorators import block_demo_users, company_required, role_required
from accounts.tenancy import get_user_company

from .choices import APPLICATION_STATUS, JOB_STATUS
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
from .selectors import (
    application_can_change,
    application_feedback,
    application_get,
    application_get_for_change,
    application_interviews,
    application_list,
    application_notes,
    application_status_changes,
    candidate_applications,
    candidate_can_download_resume,
    candidate_get,
    candidate_list,
    candidate_resume_scope,
    interview_get_for_feedback,
    job_opening_applications,
    job_opening_get,
    job_opening_list,
)
from .services import (
    APPLICATION_PREFIX,
    application_create,
    application_note_create,
    application_status_update,
    application_update,
    candidate_create,
    candidate_resume_upload,
    candidate_update,
    interview_create,
    interview_feedback_submit,
    job_opening_create,
    job_opening_update,
)


def _render_record_form(request, *, title, submit_label, sections, back_url):
    return render(
        request,
        "recruitment/candidate_form.html",
        {
            "title": title,
            "submit_label": submit_label,
            "sections": sections,
            "back_url": back_url,
        },
    )


# Applications


@role_required(*DASHBOARD_ROLES)
def application_list_view(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    return render(
        request,
        "recruitment/application_list.html",
        {
            "applications": application_list(query=query, status=status, user=request.user),
            "query": query,
            "selected_status": status,
            "application_statuses": APPLICATION_STATUS,
        },
    )


@role_required(*DASHBOARD_ROLES)
def application_detail_view(request, application_id):
    application = application_get(application_id, user=request.user)
    return render(
        request,
        "recruitment/application_detail.html",
        {
            "application": application,
            "status_form": ApplicationStatusForm(instance=application),
            "note_form": ApplicationNoteForm(),
            "interview_form": InterviewForm(company=application.candidate.company),
            "notes": application_notes(application),
            "interviews": application_interviews(application),
            "status_changes": application_status_changes(application),
            "feedback": application_feedback(application, user=request.user),
            "can_change": application_can_change(application, user=request.user),
        },
    )


@role_required(*RECRUITMENT_ROLES)
def application_update_view(request, application_id):
    application = application_get_for_change(application_id, user=request.user)
    form = ApplicationForm(
        instance=application,
        user=request.user,
        company=application.candidate.company,
        candidate=application.candidate,
    )

    if request.method == "POST":
        updated_application, form = application_update(
            application=application, data=request.POST, user=request.user
        )
        if updated_application:
            messages.success(request, "Application updated.")
            return redirect(
                "recruitment:application_detail", application_id=updated_application.id
            )

    return _render_record_form(
        request,
        title="Edit application",
        submit_label="Update application",
        sections=[("Application", form)],
        back_url=reverse("recruitment:application_detail", args=[application.id]),
    )


@role_required(*RECRUITMENT_ROLES)
def application_status_update_view(request, application_id):
    application = application_get_for_change(application_id, user=request.user)

    if request.method == "POST":
        updated_application, form = application_status_update(
            application=application, data=request.POST, user=request.user
        )
        if updated_application:
            messages.success(request, "Application status updated.")
        else:
            messages.error(request, "Please choose a valid status.")

    return redirect("recruitment:application_detail", application_id=application.id)


@role_required(*DASHBOARD_ROLES)
def application_note_create_view(request, application_id):
    application = application_get_for_change(application_id, user=request.user)

    if request.method == "POST":
        note, form = application_note_create(
            application=application, data=request.POST, author=request.user
        )
        if note:
            messages.success(request, "Note added.")
        else:
            messages.error(request, "Please enter a note.")

    return redirect("recruitment:application_detail", application_id=application.id)


@role_required(*RECRUITMENT_ROLES)
def interview_create_view(request, application_id):
    application = application_get_for_change(application_id, user=request.user)

    if request.method == "POST":
        interview, form = interview_create(application=application, data=request.POST)
        if interview:
            messages.success(request, "Interview scheduled.")
        else:
            messages.error(request, "Please check the interview details.")

    return redirect("recruitment:application_detail", application_id=application.id)


@role_required(*DASHBOARD_ROLES)
def interview_feedback_view(request, interview_id):
    interview = interview_get_for_feedback(interview_id, user=request.user)
    form = InterviewFeedbackForm(instance=getattr(interview, "feedback", None))

    if request.method == "POST":
        feedback, form = interview_feedback_submit(
            interview=interview, data=request.POST, user=request.user
        )
        if feedback:
            messages.success(request, "Feedback saved.")
            return redirect(
                "recruitment:application_detail", application_id=interview.application_id
            )

    return render(
        request,
        "recruitment/interview_feedback.html",
        {"interview": interview, "form": form},
    )


# Candidates (the people)


@role_required(*RECRUITMENT_ROLES)
def candidate_list_view(request):
    query = request.GET.get("q", "").strip()

    return render(
        request,
        "recruitment/candidate_list.html",
        {
            "candidates": candidate_list(query=query, user=request.user),
            "query": query,
        },
    )


@role_required(*RECRUITMENT_ROLES)
@company_required("recruitment:candidate_list")
def candidate_create_view(request):
    company = get_user_company(request.user)
    candidate_form = CandidateForm(company=company)
    application_form = ApplicationForm(
        user=request.user, company=company, prefix=APPLICATION_PREFIX
    )

    if request.method == "POST":
        candidate, created, candidate_form, application_form = candidate_create(
            data=request.POST, user=request.user
        )
        if candidate:
            if created:
                messages.success(request, "Candidate added successfully.")
            else:
                messages.success(
                    request,
                    "This person was already a candidate, so the new application was added "
                    "to their existing profile. Their details were not changed.",
                )
            return redirect("recruitment:candidate_detail", candidate_id=candidate.id)

    return _render_record_form(
        request,
        title="Add candidate",
        submit_label="Save candidate",
        sections=[("Candidate", candidate_form), ("First application", application_form)],
        back_url=reverse("recruitment:candidate_list"),
    )


@role_required(*RECRUITMENT_ROLES)
def candidate_detail_view(request, candidate_id):
    candidate = candidate_get(candidate_id, user=request.user)
    return render(
        request,
        "recruitment/candidate_detail.html",
        {
            "candidate": candidate,
            "applications": candidate_applications(candidate, user=request.user),
            "resume_form": ResumeUploadForm(),
            "can_download_resume": candidate_can_download_resume(candidate, user=request.user),
        },
    )


@role_required(*RECRUITMENT_ROLES)
@block_demo_users
def candidate_resume_upload_view(request, candidate_id):
    candidate = candidate_get(candidate_id, user=request.user)

    if request.method == "POST":
        updated_candidate, form = candidate_resume_upload(
            candidate=candidate, data=request.POST, files=request.FILES
        )
        if updated_candidate:
            messages.success(request, "Resume uploaded.")
        else:
            messages.error(request, " ".join(form.errors.get("resume", ["Upload failed."])))

    return redirect("recruitment:candidate_detail", candidate_id=candidate.id)


@role_required(*DASHBOARD_ROLES)
def candidate_resume_download_view(request, candidate_id):
    candidate = get_object_or_404(candidate_resume_scope(request.user), id=candidate_id)
    if not candidate.resume:
        raise Http404("No resume uploaded.")

    response = FileResponse(
        candidate.resume.open("rb"),
        as_attachment=True,
        filename=candidate.resume_original_name or "resume",
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@role_required(*RECRUITMENT_ROLES)
def candidate_update_view(request, candidate_id):
    candidate = candidate_get(candidate_id, user=request.user)
    form = CandidateForm(instance=candidate, company=candidate.company)

    if request.method == "POST":
        updated_candidate, form = candidate_update(candidate=candidate, data=request.POST)
        if updated_candidate:
            messages.success(request, "Candidate updated successfully.")
            return redirect("recruitment:candidate_detail", candidate_id=updated_candidate.id)

    return _render_record_form(
        request,
        title="Edit candidate",
        submit_label="Update candidate",
        sections=[("Candidate", form)],
        back_url=reverse("recruitment:candidate_detail", args=[candidate.id]),
    )


@role_required(*RECRUITMENT_ROLES)
def application_create_view(request, candidate_id):
    candidate = candidate_get(candidate_id, user=request.user)
    form = ApplicationForm(user=request.user, company=candidate.company, candidate=candidate)

    if request.method == "POST":
        application, form = application_create(
            candidate=candidate, data=request.POST, user=request.user
        )
        if application:
            messages.success(request, "Application added.")
            return redirect("recruitment:application_detail", application_id=application.id)

    return _render_record_form(
        request,
        title=f"New application for {candidate.full_name}",
        submit_label="Add application",
        sections=[("Application", form)],
        back_url=reverse("recruitment:candidate_detail", args=[candidate.id]),
    )


# Jobs


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
    job = job_opening_get(job_id, user=request.user)
    return render(
        request,
        "recruitment/job_opening_detail.html",
        {"job": job, "applications": job_opening_applications(job, user=request.user)},
    )


@role_required(*RECRUITMENT_ROLES)
@company_required("recruitment:job_opening_list")
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
