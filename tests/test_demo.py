import re

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.urls import reverse

from accounts.choices import ROLE_HR_ADMIN, ROLE_RECRUITER
from accounts.demo import DEMO_COMPANY_NAME, DEMO_USERS, is_demo_user
from accounts.factories import CompanyFactory, UserFactory
from accounts.models import Invitation
from recruitment.factories import ApplicationFactory, CandidateFactory
from recruitment.models import (
    Application,
    ApplicationStatusChange,
    Candidate,
    InterviewFeedback,
)

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture(autouse=True)
def resume_storage(tmp_path, monkeypatch):
    storage = FileSystemStorage(location=tmp_path)
    monkeypatch.setattr(Candidate._meta.get_field("resume"), "storage", storage)
    return storage


@pytest.fixture
def demo_on(settings):
    settings.DEMO_MODE = True


@pytest.fixture
def demo_company():
    return CompanyFactory(name=DEMO_COMPANY_NAME)


@pytest.fixture
def demo_hr_admin(demo_company):
    user = UserFactory(username="demo_hr_admin", role=ROLE_HR_ADMIN, company=demo_company)
    user.set_unusable_password()
    user.save()
    return user


@pytest.fixture
def demo_recruiter(demo_company):
    return UserFactory(username="demo_recruiter", role=ROLE_RECRUITER, company=demo_company)


# One-click demo login


def test_demo_login_is_off_unless_demo_mode(client):
    call_command("seed_demo")

    assert client.post(reverse("accounts:demo_login", args=["recruiter"])).status_code == 404
    assert "Log in as" not in client.get(reverse("accounts:login")).content.decode()


@pytest.mark.parametrize("role", list(DEMO_USERS))
def test_demo_login_signs_in_as_that_role(client, demo_on, role):
    call_command("seed_demo")

    response = client.post(reverse("accounts:demo_login", args=[role]))

    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")
    user = User.objects.get(pk=client.session["_auth_user_id"])
    assert user.username == DEMO_USERS[role]["username"]
    assert is_demo_user(user)


def test_login_page_shows_demo_buttons_in_demo_mode(client, demo_on):
    content = client.get(reverse("accounts:login")).content.decode()

    for account in DEMO_USERS.values():
        assert f"Log in as {account['label']}" in content


def test_demo_login_requires_post_and_a_known_role(client, demo_on):
    call_command("seed_demo")

    assert client.get(reverse("accounts:demo_login", args=["recruiter"])).status_code == 405
    assert client.post(reverse("accounts:demo_login", args=["superuser"])).status_code == 404


# seed_demo


def test_seed_demo_is_safe_to_rerun():
    call_command("seed_demo")
    counts = (
        Application.objects.count(),
        ApplicationStatusChange.objects.count(),
        InterviewFeedback.objects.count(),
        Candidate.objects.count(),
    )

    call_command("seed_demo")

    assert (
        Application.objects.count(),
        ApplicationStatusChange.objects.count(),
        InterviewFeedback.objects.count(),
        Candidate.objects.count(),
    ) == counts


def test_seed_demo_covers_every_status_and_attaches_resumes(resume_storage):
    call_command("seed_demo")

    statuses = set(Application.objects.values_list("status", flat=True))
    assert statuses == {"applied", "screening", "interview", "assessment", "offer", "hired", "rejected"}
    with_resume = Candidate.objects.exclude(resume="")
    assert with_resume.exists()
    with resume_storage.open(with_resume.first().resume.name) as stored:
        assert stored.read(5) == b"%PDF-"


def test_seed_demo_users_cannot_log_in_with_a_password_or_reach_admin(client):
    call_command("seed_demo")

    for account in DEMO_USERS.values():
        user = User.objects.get(username=account["username"])
        assert not user.has_usable_password()
        assert not (user.is_staff or user.is_superuser)
        assert authenticate(username=user.username, password="") is None
        client.force_login(user)
        response = client.get("/admin/password_change/")
        assert response.status_code == 302
        assert response.url.startswith("/admin/login/")


def test_seed_demo_refuses_to_take_over_a_real_account():
    UserFactory(username="demo_recruiter")

    with pytest.raises(CommandError, match="not a demo account"):
        call_command("seed_demo")


# Demo accounts are read-only for invites and resumes


def test_demo_hr_admin_cannot_create_invites(client, demo_hr_admin):
    client.force_login(demo_hr_admin)

    response = client.post(
        reverse("accounts:invitation_list"), {"email": "x@example.com", "role": ROLE_RECRUITER}
    )

    assert response.status_code == 403
    assert not Invitation.objects.exists()
    page = client.get(reverse("accounts:invitation_list")).content.decode()
    assert "disabled in the demo" in page
    assert 'name="email"' not in page


def test_demo_hr_admin_cannot_revoke_invites(client, demo_hr_admin, demo_company):
    invitation = Invitation.objects.create(
        company=demo_company, email="x@example.com", role=ROLE_RECRUITER
    )
    client.force_login(demo_hr_admin)

    response = client.post(reverse("accounts:invitation_revoke", args=[invitation.id]))

    assert response.status_code == 403
    assert Invitation.objects.filter(pk=invitation.pk).exists()


def test_demo_recruiter_cannot_upload_resumes(client, demo_recruiter, demo_company):
    candidate = CandidateFactory(company=demo_company)
    ApplicationFactory(candidate=candidate, job=None)
    client.force_login(demo_recruiter)

    response = client.post(
        reverse("recruitment:candidate_resume_upload", args=[candidate.id]),
        {"resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4 demo")},
    )

    assert response.status_code == 403
    candidate.refresh_from_db()
    assert not candidate.resume
    page = client.get(reverse("recruitment:candidate_detail", args=[candidate.id])).content.decode()
    assert "Resume uploads are disabled in the demo." in page


def test_demo_user_can_still_download_seeded_resumes(client, demo_on):
    call_command("seed_demo")
    candidate = Candidate.objects.exclude(resume="").first()
    client.post(reverse("accounts:demo_login", args=["hr-admin"]))

    response = client.get(reverse("recruitment:candidate_resume", args=[candidate.id]))

    assert response.status_code == 200


def test_same_username_outside_the_demo_company_is_not_a_demo_user(client):
    user = UserFactory(username="demo_hr_admin", role=ROLE_HR_ADMIN)
    client.force_login(user)

    response = client.post(
        reverse("accounts:invitation_list"), {"email": "x@example.com", "role": ROLE_RECRUITER}
    )

    assert not is_demo_user(user)
    assert response.status_code == 302


# Reserved names


def test_signup_rejects_demo_usernames_and_company_name(client):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "Demo_Recruiter",
            "first_name": "X",
            "email": "x@example.com",
            "company_name": DEMO_COMPANY_NAME.upper(),
            "password1": "S3cure-pass-123",
            "password2": "S3cure-pass-123",
        },
    )

    errors = response.context["form"].errors
    assert "username" in errors
    assert "company_name" in errors


def test_invite_acceptance_rejects_demo_usernames(client, company, hr_admin):
    invitation = Invitation.objects.create(company=company, email="x@example.com", role=ROLE_RECRUITER)

    response = client.post(
        reverse("accounts:invitation_accept", args=[invitation.token]),
        {"username": "demo_hr_admin", "first_name": "X", "password1": "S3cure-pass-123", "password2": "S3cure-pass-123"},
    )

    assert "username" in response.context["form"].errors


# setup_test_users


def test_setup_test_users_generates_and_prints_a_password(capsys):
    call_command("setup_test_users")

    output = capsys.readouterr().out
    password = re.search(r"Generated password: (\S+)", output).group(1)
    assert len(password) >= 12
    assert authenticate(username="recruiter", password=password) is not None
    assert password not in output.replace(f"Generated password: {password}", "")


def test_setup_test_users_uses_the_given_password():
    call_command("setup_test_users", password="Given-pass-123")

    assert authenticate(username="hradmin", password="Given-pass-123") is not None
