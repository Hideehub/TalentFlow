import pytest

from accounts.choices import ROLE_HR_ADMIN
from accounts.factories import UserFactory
from recruitment.factories import ApplicationFactory, JobOpeningFactory

pytestmark = pytest.mark.django_db


def test_user_factory_sets_role_and_company(company):
    user = UserFactory(role=ROLE_HR_ADMIN, company=company)

    assert list(user.groups.values_list("name", flat=True)) == [ROLE_HR_ADMIN]
    assert user.profile.company == company
    assert user.check_password("password123")


def test_user_factory_can_skip_role_and_company():
    user = UserFactory(role="", company=False)

    assert not user.groups.exists()
    assert not hasattr(user, "profile")


def test_application_factory_puts_candidate_in_job_company(company):
    job = JobOpeningFactory(company=company)
    application = ApplicationFactory(job=job)

    assert application.candidate.company == company
    assert application.position == job.title


def test_application_factory_without_job_uses_imported_position():
    application = ApplicationFactory(job=None)

    assert application.job is None
    assert application.position == "Imported role"


def test_role_fixtures_share_one_company(recruiter, hiring_manager, hr_admin, company):
    assert {
        recruiter.profile.company,
        hiring_manager.profile.company,
        hr_admin.profile.company,
    } == {company}
