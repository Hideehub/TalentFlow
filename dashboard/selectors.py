from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from recruitment.models import Interview
from recruitment.selectors import candidate_scope


def dashboard_summary(user=None):
    today = timezone.localdate()
    week_end = today + timedelta(days=7)
    candidates = candidate_scope(user)

    return {
        "candidate_count": candidates.count(),
        "interviews_this_week": Interview.objects.filter(
            candidate__in=candidates,
            scheduled_at__date__gte=today,
            scheduled_at__date__lte=week_end,
            status="scheduled",
        ).count(),
        "offers_sent": candidates.filter(status="offer").count(),
        "hired_count": candidates.filter(status="hired").count(),
    }


def candidates_by_status(user=None):
    return candidate_scope(user).values("status").annotate(total=Count("id")).order_by("status")


def hardest_roles(user=None, limit=5):
    return (
        candidate_scope(user).values("position_applied_for")
        .annotate(total=Count("id"))
        .order_by("-total", "position_applied_for")[:limit]
    )


def upcoming_interviews(user=None, limit=5):
    return (
        Interview.objects.select_related("candidate")
        .filter(
            candidate__in=candidate_scope(user),
            status="scheduled",
            scheduled_at__gte=timezone.now(),
        )
        .order_by("scheduled_at")[:limit]
    )
