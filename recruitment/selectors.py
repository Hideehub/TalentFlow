from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from accounts.choices import ROLE_HIRING_MANAGER, ROLE_HR_ADMIN, ROLE_RECRUITER
from accounts.decorators import user_has_role
from accounts.tenancy import get_user_company

from .models import Candidate, Interview, JobOpening


def _is_hr_admin(user):
    return user and user.is_authenticated and (
        user.is_superuser or user_has_role(user, (ROLE_HR_ADMIN,))
    )


def _is_recruiter(user):
    return user and user.is_authenticated and user_has_role(user, (ROLE_RECRUITER,))


def _is_hiring_manager(user):
    return user and user.is_authenticated and user_has_role(user, (ROLE_HIRING_MANAGER,))


def candidate_scope(user):
    candidates = Candidate.objects.select_related("job", "assigned_recruiter")
    company = get_user_company(user)

    if user and user.is_authenticated and user.is_superuser:
        return candidates

    if not company:
        return candidates.none()

    candidates = candidates.filter(company=company)

    if _is_hr_admin(user):
        return candidates

    if _is_recruiter(user):
        return candidates.filter(Q(assigned_recruiter=user) | Q(assigned_recruiter__isnull=True))

    if _is_hiring_manager(user):
        return candidates

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
        return "Your assigned candidates and unassigned imports."
    if _is_hiring_manager(user):
        return "Company hiring activity for candidate review."
    return "Recruitment activity at a glance."


def candidate_list(*, query="", status="", user=None):
    candidates = candidate_scope(user)

    if query:
        candidates = candidates.filter(
            Q(full_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(position_applied_for__icontains=query)
            | Q(job__title__icontains=query)
        )

    if status:
        candidates = candidates.filter(status=status)

    return candidates.order_by("-created_at")


def candidate_get(candidate_id, *, user=None):
    return get_object_or_404(candidate_scope(user), id=candidate_id)


def candidate_notes(candidate):
    return candidate.notes.all().order_by("-created_at")


def candidate_interviews(candidate):
    return candidate.interviews.all().order_by("scheduled_at")


def upcoming_interviews(user=None):
    return Interview.objects.select_related("candidate").filter(
        candidate__in=candidate_scope(user),
        status="scheduled",
    ).order_by("scheduled_at")


def job_opening_list(*, query="", status="", user=None):
    jobs = job_opening_scope(user).annotate(
        candidate_count=Count("candidates")
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
    return get_object_or_404(
        job_opening_scope(user).prefetch_related("candidates"),
        id=job_id,
    )
