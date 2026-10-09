import pytest
from django.urls import reverse

from recruitment.factories import ApplicationFactory, CandidateFactory, JobOpeningFactory
from recruitment.models import ApplicationStatusChange
from recruitment.services import (
    application_create,
    application_status_update,
    application_update,
    candidate_create,
)
from tests.test_import import run_import

pytestmark = pytest.mark.django_db


@pytest.fixture
def job(company):
    return JobOpeningFactory(company=company, title="Backend Engineer")


def changes(application):
    return list(
        application.status_changes.values_list("from_status", "to_status", "changed_by")
    )


def test_creating_a_candidate_logs_the_initial_status(recruiter, job):
    data = {
        "full_name": "Ada",
        "email": "ada@example.com",
        "phone": "1",
        "years_of_experience": 3,
        "source": "referral",
        "application-job": job.id,
        "application-status": "screening",
    }

    candidate, *_rest = candidate_create(data=data, user=recruiter)

    assert changes(candidate.applications.get()) == [("", "screening", recruiter.id)]


def test_adding_an_application_logs_the_initial_status(hr_admin, job, company):
    candidate = CandidateFactory(company=company)

    application, _form = application_create(
        candidate=candidate, data={"job": job.id, "status": "applied"}, user=hr_admin
    )

    assert changes(application) == [("", "applied", hr_admin.id)]


def test_status_update_logs_from_to_and_who(hr_admin, job):
    application = ApplicationFactory(job=job, status="applied")

    application_status_update(application=application, data={"status": "offer"}, user=hr_admin)

    assert changes(application) == [("applied", "offer", hr_admin.id)]


def test_unchanged_status_logs_nothing(hr_admin, job):
    application = ApplicationFactory(job=job, status="applied")

    application_status_update(application=application, data={"status": "applied"}, user=hr_admin)
    application_update(
        application=application, data={"job": job.id, "status": "applied"}, user=hr_admin
    )

    assert not ApplicationStatusChange.objects.exists()


def test_editing_an_application_logs_a_status_change(hr_admin, job):
    application = ApplicationFactory(job=job, status="screening")

    application_update(
        application=application, data={"job": job.id, "status": "rejected"}, user=hr_admin
    )

    assert changes(application) == [("screening", "rejected", hr_admin.id)]


def test_import_logs_the_initial_status_of_each_application(hr_admin, job):
    run_import(
        hr_admin,
        ("Ada", "ada@example.com", "0800", "Backend Engineer", 3, "interview"),
        ("Grace", "grace@example.com", "0800", "Data Wizard", 3, "applied"),
    )

    assert sorted(
        ApplicationStatusChange.objects.values_list("from_status", "to_status", "changed_by")
    ) == [("", "applied", hr_admin.id), ("", "interview", hr_admin.id)]


def test_status_view_records_the_signed_in_user_and_timeline_is_shown(
    client, recruiter, hiring_manager, company
):
    job = JobOpeningFactory(company=company, hiring_manager=hiring_manager)
    application = ApplicationFactory(job=job, assigned_recruiter=recruiter, status="applied")
    client.force_login(recruiter)

    client.post(
        reverse("recruitment:application_status_update", args=[application.id]),
        {"status": "screening"},
    )

    assert changes(application) == [("applied", "screening", recruiter.id)]
    client.force_login(hiring_manager)
    page = client.get(reverse("recruitment:application_detail", args=[application.id]))
    assert "Applied → Screening" in page.content.decode()
