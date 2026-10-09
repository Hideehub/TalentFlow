import pytest
from django.urls import reverse

from accounts.choices import ROLE_RECRUITER
from accounts.factories import UserFactory
from recruitment.factories import ApplicationFactory, CandidateFactory, JobOpeningFactory
from reports.selectors import application_source_report

pytestmark = pytest.mark.django_db


def test_applications_by_source_counts_scoped_applications(hr_admin, company):
    job = JobOpeningFactory(company=company)
    referral = CandidateFactory(company=company, source="referral")
    ApplicationFactory(candidate=referral, job=job)
    ApplicationFactory(candidate=referral, job=JobOpeningFactory(company=company))
    ApplicationFactory(candidate=CandidateFactory(company=company, source="linkedin"), job=job)
    ApplicationFactory(candidate=CandidateFactory(source="agency"))  # another company

    assert application_source_report(hr_admin) == [
        {"source": "Referral", "total": 2},
        {"source": "LinkedIn", "total": 1},
    ]


def test_source_report_follows_recruiter_scope(company):
    recruiter = UserFactory(role=ROLE_RECRUITER, company=company)
    other = UserFactory(role=ROLE_RECRUITER, company=company)
    job = JobOpeningFactory(company=company)
    ApplicationFactory(candidate=CandidateFactory(company=company, source="referral"), job=job, assigned_recruiter=recruiter)
    ApplicationFactory(candidate=CandidateFactory(company=company, source="agency"), job=job, assigned_recruiter=other)

    assert application_source_report(recruiter) == [{"source": "Referral", "total": 1}]


def test_reports_page_shows_source_table(client, hr_admin, company):
    ApplicationFactory(candidate=CandidateFactory(company=company, source="referral"), job=JobOpeningFactory(company=company))
    client.force_login(hr_admin)

    content = client.get(reverse("reports:home")).content.decode()

    assert "Applications by source" in content
    assert "Referral" in content
