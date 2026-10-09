from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from accounts.choices import ROLE_HIRING_MANAGER, ROLE_HR_ADMIN, ROLE_RECRUITER
from accounts.decorators import user_has_role
from accounts.tenancy import get_user_company

from .models import Application, Candidate, Interview, JobOpening


def _is_hr_admin(user):
    return user and user.is_authenticated and (
        user.is_superuser or user_has_role(user, (ROLE_HR_ADMIN,))
    )


def _is_recruiter(user):
    return user and user.is_authenticated and user_has_role(user, (ROLE_RECRUITER,))


def _is_hiring_manager(user):
    return user and user.is_authenticated and user_has_role(user, (ROLE_HIRING_MANAGER,))


def application_scope(user):
    applications = Application.objects.select_related(
        "candidate", "job", "assigned_recruiter"
    )
    company = get_user_company(user)

    if user and user.is_authenticated and user.is_superuser:
        return applications

    if not company:
        return applications.none()

    applications = applications.filter(candidate__company=company)

    if _is_hr_admin(user):
        return applications

    if _is_recruiter(user):
        return applications.filter(
            Q(assigned_recruiter=user) | Q(assigned_recruiter__isnull=True)
        )

    if _is_hiring_manager(user):
        return applications.filter(job__hiring_manager=user)

    return applications.none()


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


def application_notes(application):
    return application.notes.select_related("author").order_by("-created_at")


def application_interviews(application):
    return application.interviews.select_related("interviewer").order_by("scheduled_at")


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
