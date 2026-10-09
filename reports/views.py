from django.shortcuts import render

from accounts.choices import DASHBOARD_ROLES
from accounts.decorators import role_required

from .selectors import (
    application_source_report,
    candidate_role_report,
    candidate_status_report,
    interview_week_report,
    recruitment_summary_report,
)


@role_required(*DASHBOARD_ROLES)
def reports_home_view(request):
    return render(
        request,
        "reports/home.html",
        {
            "summary": recruitment_summary_report(request.user),
            "status_rows": candidate_status_report(request.user),
            "role_rows": candidate_role_report(request.user),
            "source_rows": application_source_report(request.user),
            "interviews": interview_week_report(request.user),
        },
    )
