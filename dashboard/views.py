from django.shortcuts import render

from accounts.choices import DASHBOARD_ROLES
from accounts.decorators import role_required

from .selectors import (
    candidates_by_status,
    dashboard_summary,
    hardest_roles,
    upcoming_interviews,
)
from recruitment.selectors import dashboard_scope_label, interviews_awaiting_feedback


@role_required(*DASHBOARD_ROLES)
def dashboard_home_view(request):
    return render(
        request,
        "dashboard/home.html",
        {
            "summary": dashboard_summary(request.user),
            "status_rows": candidates_by_status(request.user),
            "hardest_roles": hardest_roles(request.user),
            "upcoming_interviews": upcoming_interviews(request.user),
            "scope_label": dashboard_scope_label(request.user),
            "awaiting_feedback": interviews_awaiting_feedback(request.user),
        },
    )
