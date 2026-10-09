import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse

from accounts.choices import ROLE_HR_ADMIN, ROLE_RECRUITER
from accounts.factories import CompanyFactory
from accounts.forms import SignUpForm
from accounts.models import Company

pytestmark = pytest.mark.django_db

User = get_user_model()
SIGNUP_URL = reverse("accounts:signup")


def signup_data(**overrides):
    data = {
        "username": "ada",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "company_name": "Acme",
        "password1": "S3cure-pass-123",
        "password2": "S3cure-pass-123",
    }
    data.update(overrides)
    return data


def role_names(user):
    return list(user.groups.values_list("name", flat=True))


def test_signup_creates_new_company_with_user_as_hr_admin(client):
    response = client.post(SIGNUP_URL, signup_data())

    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")
    user = User.objects.get(username="ada")
    assert user.profile.company.name == "Acme"
    assert role_names(user) == [ROLE_HR_ADMIN]
    assert client.session["_auth_user_id"] == str(user.pk)


def test_signup_ignores_a_posted_role(client):
    client.post(SIGNUP_URL, signup_data(role=ROLE_RECRUITER))

    assert role_names(User.objects.get(username="ada")) == [ROLE_HR_ADMIN]


def test_signup_rejects_taken_company_name_case_insensitively(client):
    CompanyFactory(name="Acme")

    response = client.post(SIGNUP_URL, signup_data(company_name="  acme "))

    assert response.status_code == 200
    assert "company_name" in response.context["form"].errors
    assert not User.objects.filter(username="ada").exists()
    assert Company.objects.count() == 1


def test_signup_rolls_back_everything_when_a_later_step_fails(client, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("accounts.services._join_company", fail)

    with pytest.raises(RuntimeError):
        client.post(SIGNUP_URL, signup_data())

    assert not User.objects.filter(username="ada").exists()
    assert not Company.objects.filter(name="Acme").exists()


def test_simultaneous_duplicate_company_shows_form_error(client, monkeypatch):
    # Simulate losing the race: the form's check passes, then the insert hits the constraint.
    CompanyFactory(name="Acme")
    monkeypatch.setattr(
        SignUpForm, "clean_company_name", lambda form: form.cleaned_data["company_name"].strip()
    )

    response = client.post(SIGNUP_URL, signup_data(company_name="acme"))

    assert response.status_code == 200
    assert "company_name" in response.context["form"].errors
    assert not User.objects.filter(username="ada").exists()
    assert Company.objects.count() == 1


def test_database_rejects_company_name_differing_only_by_case():
    CompanyFactory(name="Acme")

    with pytest.raises(IntegrityError), transaction.atomic():
        Company.objects.create(name="ACME")
