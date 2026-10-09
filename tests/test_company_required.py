import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from accounts.factories import UserFactory
from recruitment.models import JobOpening

pytestmark = pytest.mark.django_db


@pytest.fixture
def companyless_superuser(client):
    user = UserFactory(role="", company=False, is_superuser=True)
    client.force_login(user)
    return user


def messages_text(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


def test_superuser_without_company_cannot_create_job(client, companyless_superuser):
    url = reverse("recruitment:job_opening_create")

    get_response = client.get(url)
    post_response = client.post(url, {"title": "Dev", "department": "Engineering"})

    assert get_response.status_code == 302
    assert get_response.url == reverse("recruitment:job_opening_list")
    assert post_response.status_code == 302
    assert any("isn't linked to a company" in text for text in messages_text(post_response))
    assert not JobOpening.objects.exists()


@pytest.mark.parametrize(
    "url_name", ["uploads:candidate_import", "uploads:candidate_import_confirm"]
)
def test_superuser_without_company_cannot_import(client, companyless_superuser, url_name):
    response = client.post(reverse(url_name))

    assert response.status_code == 302
    assert response.url == reverse("recruitment:candidate_list")
    assert any("isn't linked to a company" in text for text in messages_text(response))


def test_superuser_without_company_cannot_add_candidate(client, companyless_superuser):
    response = client.get(reverse("recruitment:candidate_create"))

    assert response.status_code == 302
    assert response.url == reverse("recruitment:candidate_list")


def test_user_with_company_can_still_open_job_and_import_pages(client, hr_admin):
    client.force_login(hr_admin)

    assert client.get(reverse("recruitment:job_opening_create")).status_code == 200
    assert client.get(reverse("uploads:candidate_import")).status_code == 200
    assert client.get(reverse("recruitment:candidate_create")).status_code == 200
