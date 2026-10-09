import pytest

from accounts.choices import ROLE_HIRING_MANAGER, ROLE_HR_ADMIN, ROLE_RECRUITER
from accounts.factories import CompanyFactory, UserFactory


@pytest.fixture
def company(db):
    return CompanyFactory()


@pytest.fixture
def recruiter(company):
    return UserFactory(role=ROLE_RECRUITER, company=company)


@pytest.fixture
def hiring_manager(company):
    return UserFactory(role=ROLE_HIRING_MANAGER, company=company)


@pytest.fixture
def hr_admin(company):
    return UserFactory(role=ROLE_HR_ADMIN, company=company)
