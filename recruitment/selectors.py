from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.choices import ROLE_HIRING_MANAGER, ROLE_HR_ADMIN, ROLE_RECRUITER
from accounts.decorators import user_has_role
from accounts.tenancy import get_user_company

from .models import Application, Candidate, Interview, InterviewFeedback, JobOpening


def _is_hr_admin(user):
    return user and user.is_authenticated and (
        user.is_superuser or user_has_role(user, (ROLE_HR_ADMIN,))
    )


def _is_recruiter(user):
    return user and user.is_authenticated and user_has_role(user, (ROLE_RECRUITER,))


def _is_hiring_manager(user):
    return user and user.is_authenticated and user_has_role(user, (ROLE_HIRING_MANAGER,))


def _role_filter(user):
    """What a user's role lets them work on. None means the whole company."""
    if _is_hr_admin(user):
        return None
    if _is_recruiter(user):
        return Q(assigned_recruiter=user) | Q(assigned_recruiter__isnull=True)
    if _is_hiring_manager(user):
        return Q(job__hiring_manager=user)
    return Q(pk__in=[])


def _company_applications(user):
    applications = Application.objects.select_related(
        "candidate", "job", "assigned_recruiter"
    )
    if user and user.is_authenticated and user.is_superuser:
        return applications
    company = get_user_company(user)
    if not company:
        return applications.none()
    return applications.filter(candidate__company=company)


def application_manage_scope(user):
    """Applications the user may change (status, edit, interviews, notes) by role."""
    applications = _company_applications(user)
    if user and user.is_authenticated and user.is_superuser:
        return applications
    role_filter = _role_filter(user)
    return applications if role_filter is None else applications.filter(role_filter)


def application_scope(user):
    """Applications the user may view: their role's scope, or ones they interview for."""
    applications = _company_applications(user)
    if not (user and user.is_authenticated):
        return applications.none()
    if user.is_superuser:
        return applications
    role_filter = _role_filter(user)
    if role_filter is None:
        return applications
    # A subquery rather than a join, so counts and aggregates don't see duplicate rows.
    interviewing = Q(id__in=Interview.objects.filter(interviewer=user).values("application_id"))
    return applications.filter(role_filter | interviewing)


def candidate_scope(user):
    candidates = Candidate.objects.all()
    company = get_user_company(user)

    if user and user.is_authenticated and user.is_superuser:
        return candidates

    if not company:
        return candidates.none()

    candidates = candidates.filter(company=company)

    if _is_hr_admin(user) or _is_recruiter(user):
        return candidates

    if _is_hiring_manager(user):
        return candidates.filter(applications__in=application_scope(user)).distinct()

    return candidates.none()


def job_opening_scope(user):
    jobs = JobOpening.objects.all()
    company = get_user_company(user)

    if user and user.is_authenticated and user.is_superuser:
        return jobs

    if not company:
        return jobs.none()

    jobs = jobs.filter(company=company)

    return jobs


def dashboard_scope_label(user):
    if _is_hr_admin(user):
        return "Company-wide recruitment activity."
    if _is_recruiter(user):
        return "Your assigned applications and unassigned imports."
    if _is_hiring_manager(user):
        return "Applications for the jobs you manage."
    return "Recruitment activity at a glance."


def application_list(*, query="", status="", user=None):
    applications = application_scope(user)

    if query:
        applications = applications.filter(
            Q(candidate__full_name__icontains=query)
            | Q(candidate__email__icontains=query)
            | Q(candidate__phone__icontains=query)
            | Q(job__title__icontains=query)
            | Q(imported_position__icontains=query)
        )

    if status:
        applications = applications.filter(status=status)

    return applications.order_by("-created_at")


def application_get(application_id, *, user=None):
    return get_object_or_404(application_scope(user), id=application_id)


def application_get_for_change(application_id, *, user=None):
    return get_object_or_404(application_manage_scope(user), id=application_id)


def application_can_change(application, *, user=None):
    return application_manage_scope(user).filter(pk=application.pk).exists()


def application_status_changes(application):
    return application.status_changes.select_related("changed_by").order_by("created_at")


def application_notes(application):
    return application.notes.select_related("author").order_by("-created_at")


def application_interviews(application):
    return application.interviews.select_related("interviewer", "feedback").order_by(
        "scheduled_at"
    )


def _sees_all_feedback(application, user):
    return (
        _is_hr_admin(user)
        or application.assigned_recruiter_id == user.id
        or (application.job_id is not None and application.job.hiring_manager_id == user.id)
    )


def application_feedback(application, *, user):
    """Feedback the user may read on this application.

    HR Admins, the owning recruiter and the job's hiring manager see everything. An
    interviewer sees everyone's feedback only after submitting their own, so earlier
    opinions can't anchor theirs. Anyone else sees none.
    """
    feedback = InterviewFeedback.objects.filter(interview__application=application).select_related(
        "author", "interview"
    ).order_by("created_at")
    if _sees_all_feedback(application, user) or feedback.filter(author=user).exists():
        return feedback
    return feedback.none()


def interview_get_for_feedback(interview_id, *, user):
    """Only the assigned interviewer can give feedback on an interview."""
    return get_object_or_404(
        Interview.objects.select_related("application__candidate", "application__job"),
        id=interview_id,
        interviewer=user,
    )


def interviews_awaiting_feedback(user, limit=5):
    return (
        Interview.objects.select_related("application__candidate")
        .filter(interviewer=user, feedback__isnull=True, scheduled_at__lte=timezone.now())
        .exclude(status="cancelled")
        .order_by("scheduled_at")[:limit]
    )


def candidate_list(*, query="", user=None):
    candidates = candidate_scope(user)

    if query:
        candidates = candidates.filter(
            Q(full_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )

    return candidates.order_by("-created_at")


def candidate_get(candidate_id, *, user=None):
    return get_object_or_404(candidate_scope(user), id=candidate_id)


def candidate_resume_scope(user):
    """Candidates whose resume the user may download.

    HR Admins: everyone in the company. Everyone else (recruiters, hiring managers,
    interviewers) only people with an application they can see. Recruiters can view
    every person's basic details, but not their resume, without such an application.
    """
    candidates = candidate_scope(user)
    if _is_hr_admin(user):
        return candidates
    return candidates.filter(id__in=application_scope(user).values("candidate_id"))


def candidate_can_download_resume(candidate, *, user=None):
    return candidate_resume_scope(user).filter(pk=candidate.pk).exists()


def candidate_applications(candidate, *, user=None):
    return application_scope(user).filter(candidate=candidate).order_by("-created_at")


def upcoming_interviews(user=None):
    return Interview.objects.select_related("application__candidate").filter(
        application__in=application_scope(user),
        status="scheduled",
    ).order_by("scheduled_at")


def job_opening_list(*, query="", status="", user=None):
    jobs = job_opening_scope(user).annotate(
        candidate_count=Count("applications")
    )

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query)
            | Q(department__icontains=query)
            | Q(location__icontains=query)
        )

    if status:
        jobs = jobs.filter(status=status)

    return jobs.order_by("-created_at")


def job_opening_get(job_id, *, user=None):
    return get_object_or_404(job_opening_scope(user), id=job_id)


def job_opening_applications(job, *, user=None):
    return application_scope(user).filter(job=job).order_by("-created_at")
