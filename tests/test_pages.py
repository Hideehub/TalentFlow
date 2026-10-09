from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from recruitment.factories import ApplicationFactory, JobOpeningFactory
from recruitment.models import ApplicationNote, Interview

pytestmark = pytest.mark.django_db


def test_every_recruitment_page_renders_for_hr_admin(client, hr_admin, hiring_manager, company):
    job = JobOpeningFactory(company=company, hiring_manager=hiring_manager)
    application = ApplicationFactory(job=job)
    imported = ApplicationFactory(candidate=application.candidate, job=None)
    ApplicationNote.objects.create(application=application, note="Good call.")
    Interview.objects.create(
        application=application,
        title="Onsite",
        scheduled_at=timezone.now() + timedelta(days=1),
        interviewer=hiring_manager,
    )
    client.force_login(hr_admin)

    urls = [
        reverse("dashboard:home"),
        reverse("reports:home"),
        reverse("uploads:candidate_import"),
        reverse("recruitment:application_list"),
        reverse("recruitment:application_detail", args=[application.id]),
        reverse("recruitment:application_detail", args=[imported.id]),
        reverse("recruitment:application_update", args=[application.id]),
        reverse("recruitment:candidate_list"),
        reverse("recruitment:candidate_create"),
        reverse("recruitment:candidate_detail", args=[application.candidate.id]),
        reverse("recruitment:candidate_update", args=[application.candidate.id]),
        reverse("recruitment:application_create", args=[application.candidate.id]),
        reverse("recruitment:job_opening_list"),
        reverse("recruitment:job_opening_create"),
        reverse("recruitment:job_opening_detail", args=[job.id]),
        reverse("recruitment:job_opening_update", args=[job.id]),
    ]
    for url in urls:
        assert client.get(url).status_code == 200, url


def test_feedback_page_renders_for_the_interviewer(client, hiring_manager, company):
    application = ApplicationFactory(job=JobOpeningFactory(company=company))
    interview = Interview.objects.create(
        application=application,
        title="Onsite",
        scheduled_at=timezone.now(),
        interviewer=hiring_manager,
    )
    client.force_login(hiring_manager)

    response = client.get(reverse("recruitment:interview_feedback", args=[interview.id]))

    assert response.status_code == 200


def test_dashboard_and_reports_render_for_hiring_manager(client, hiring_manager, company):
    ApplicationFactory(job=JobOpeningFactory(company=company, hiring_manager=hiring_manager))
    client.force_login(hiring_manager)

    for url_name in ("dashboard:home", "reports:home", "recruitment:application_list"):
        response = client.get(reverse(url_name))
        assert response.status_code == 200, url_name
