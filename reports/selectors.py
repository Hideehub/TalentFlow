from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import Coalesce
from django.utils import timezone

from recruitment.models import Interview
from recruitment.selectors import application_scope


def candidate_status_report(user=None):
    return application_scope(user).values("status").annotate(total=Count("id")).order_by("status")


def candidate_role_report(user=None):
    return (
        application_scope(user)
        .annotate(position=Coalesce("job__title", "imported_position"))
        .values("position")
        .annotate(total=Count("id"))
        .order_by("-total", "position")
    )


def interview_week_report(user=None):
    today = timezone.localdate()
    week_end = today + timedelta(days=7)

    return (
        Interview.objects.select_related("application__candidate")
        .filter(
            application__in=application_scope(user),
            scheduled_at__date__gte=today,
            scheduled_at__date__lte=week_end,
        )
        .order_by("scheduled_at")
    )


def recruitment_summary_report(user=None):
    applications = application_scope(user)
    return {
        "total_candidates": applications.values("candidate").distinct().count(),
        "active_applications": applications.exclude(status__in=("hired", "rejected")).count(),
        "offers": applications.filter(status="offer").count(),
        "hired": applications.filter(status="hired").count(),
        "rejected": applications.filter(status="rejected").count(),
    }
