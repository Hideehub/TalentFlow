from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from recruitment.models import Interview
from recruitment.selectors import candidate_scope


def candidate_status_report(user=None):
    return candidate_scope(user).values("status").annotate(total=Count("id")).order_by("status")


def candidate_role_report(user=None):
    return (
        candidate_scope(user).values("position_applied_for")
        .annotate(total=Count("id"))
        .order_by("-total", "position_applied_for")
    )


def interview_week_report(user=None):
    today = timezone.localdate()
    week_end = today + timedelta(days=7)

    return (
        Interview.objects.select_related("candidate")
        .filter(
            candidate__in=candidate_scope(user),
            scheduled_at__date__gte=today,
            scheduled_at__date__lte=week_end,
        )
        .order_by("scheduled_at")
    )


def recruitment_summary_report(user=None):
    candidates = candidate_scope(user)
    return {
        "total_candidates": candidates.count(),
        "active_candidates": candidates.exclude(status__in=("hired", "rejected")).count(),
        "offers": candidates.filter(status="offer").count(),
        "hired": candidates.filter(status="hired").count(),
        "rejected": candidates.filter(status="rejected").count(),
    }
