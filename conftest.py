import pytest

from accounts.choices import ROLE_HIRING_MANAGER, ROLE_HR_ADMIN, ROLE_RECRUITER
from accounts.factories import CompanyFactory, UserFactory


@pytest.fixture(autouse=True)
def test_environment(settings):
    """Make tests independent of the local .env / CI production-like settings:
    plain HTTP requests (no HTTPS redirect) and static files without a collectstatic
    manifest."""
    settings.SECURE_SSL_REDIRECT = False
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    # Serve from app static dirs instead of a collected STATIC_ROOT (as with DEBUG on).
    settings.WHITENOISE_AUTOREFRESH = True
    settings.DEMO_MODE = False


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
