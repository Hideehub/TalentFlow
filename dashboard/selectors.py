from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import Coalesce
from django.utils import timezone

from recruitment.models import Interview
from recruitment.selectors import application_scope


def dashboard_summary(user=None):
    today = timezone.localdate()
    week_end = today + timedelta(days=7)
    applications = application_scope(user)

    return {
        "candidate_count": applications.values("candidate").distinct().count(),
        "interviews_this_week": Interview.objects.filter(
            application__in=applications,
            scheduled_at__date__gte=today,
            scheduled_at__date__lte=week_end,
            status="scheduled",
        ).count(),
        "offers_sent": applications.filter(status="offer").count(),
        "hired_count": applications.filter(status="hired").count(),
    }


def candidates_by_status(user=None):
    return application_scope(user).values("status").annotate(total=Count("id")).order_by("status")


def hardest_roles(user=None, limit=5):
    return (
        application_scope(user)
        .annotate(position=Coalesce("job__title", "imported_position"))
        .values("position")
        .annotate(total=Count("id"))
        .order_by("-total", "position")[:limit]
    )


def upcoming_interviews(user=None, limit=5):
    return (
        Interview.objects.select_related("application__candidate")
        .filter(
            application__in=application_scope(user),
            status="scheduled",
            scheduled_at__gte=timezone.now(),
        )
        .order_by("scheduled_at")[:limit]
    )
