from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.choices import ROLE_HR_ADMIN, ROLE_RECRUITER
from accounts.factories import UserFactory
from accounts.models import Invitation

pytestmark = pytest.mark.django_db

User = get_user_model()
INVITES_URL = reverse("accounts:invitation_list")
ACCEPT_DATA = {
    "username": "newbie",
    "first_name": "New",
    "last_name": "Person",
    "password1": "S3cure-pass-123",
    "password2": "S3cure-pass-123",
}


@pytest.fixture
def invitation(company, hr_admin):
    return Invitation.objects.create(
        company=company,
        email="new@example.com",
        role=ROLE_RECRUITER,
        invited_by=hr_admin,
    )


def accept_url(invitation):
    return reverse("accounts:invitation_accept", args=[invitation.token])


# Managing invites


def test_hr_admin_creates_invite_and_sees_its_link(client, hr_admin, company):
    client.force_login(hr_admin)

    response = client.post(INVITES_URL, {"email": "New@Example.com", "role": ROLE_RECRUITER})

    assert response.status_code == 302
    invitation = Invitation.objects.get()
    assert invitation.company == company
    assert invitation.email == "new@example.com"
    assert invitation.role == ROLE_RECRUITER
    assert invitation.invited_by == hr_admin
    assert invitation.expires_at > timezone.now() + timedelta(days=6)
    assert accept_url(invitation) in client.get(INVITES_URL).content.decode()


@pytest.mark.parametrize("user_fixture", ["recruiter", "hiring_manager"])
def test_only_hr_admins_can_manage_invites(client, request, user_fixture):
    client.force_login(request.getfixturevalue(user_fixture))

    assert client.get(INVITES_URL).status_code == 403


def test_second_pending_invite_for_same_email_is_rejected(client, hr_admin, invitation):
    client.force_login(hr_admin)

    response = client.post(INVITES_URL, {"email": "NEW@example.com", "role": ROLE_RECRUITER})

    assert response.status_code == 200
    assert "email" in response.context["form"].errors
    assert Invitation.objects.count() == 1


def test_existing_member_cannot_be_invited(client, hr_admin, recruiter):
    client.force_login(hr_admin)

    response = client.post(INVITES_URL, {"email": recruiter.email.upper(), "role": ROLE_RECRUITER})

    assert "email" in response.context["form"].errors
    assert not Invitation.objects.exists()


def test_hr_admin_revokes_invite(client, hr_admin, invitation):
    client.force_login(hr_admin)

    response = client.post(reverse("accounts:invitation_revoke", args=[invitation.id]))

    assert response.status_code == 302
    assert not Invitation.objects.exists()


def test_hr_admin_cannot_revoke_another_companys_invite(client, invitation):
    client.force_login(UserFactory(role=ROLE_HR_ADMIN))

    response = client.post(reverse("accounts:invitation_revoke", args=[invitation.id]))

    assert response.status_code == 404
    assert Invitation.objects.filter(pk=invitation.pk).exists()


# Accepting invites


def test_accepting_invite_joins_company_with_invited_role(client, invitation, company):
    response = client.post(accept_url(invitation), ACCEPT_DATA)

    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")
    user = User.objects.get(username="newbie")
    assert user.email == "new@example.com"
    assert user.profile.company == company
    assert list(user.groups.values_list("name", flat=True)) == [ROLE_RECRUITER]
    assert client.session["_auth_user_id"] == str(user.pk)
    invitation.refresh_from_db()
    assert invitation.accepted_at is not None


def test_invalid_accept_form_leaves_invite_usable(client, invitation):
    response = client.post(accept_url(invitation), {**ACCEPT_DATA, "password2": "different"})

    assert response.status_code == 200
    assert not User.objects.filter(username="newbie").exists()
    invitation.refresh_from_db()
    assert invitation.accepted_at is None


def test_expired_invite_cannot_be_used(client, invitation):
    invitation.expires_at = timezone.now() - timedelta(minutes=1)
    invitation.save()

    assert client.get(accept_url(invitation)).status_code == 410
    assert client.post(accept_url(invitation), ACCEPT_DATA).status_code == 410
    assert not User.objects.filter(username="newbie").exists()


def test_accepted_invite_cannot_be_reused(client, invitation):
    client.post(accept_url(invitation), ACCEPT_DATA)
    client.logout()

    response = client.post(accept_url(invitation), {**ACCEPT_DATA, "username": "second"})

    assert response.status_code == 410
    assert not User.objects.filter(username="second").exists()


def test_unknown_token_returns_404(client):
    response = client.get(reverse("accounts:invitation_accept", args=["not-a-real-token"]))

    assert response.status_code == 404
