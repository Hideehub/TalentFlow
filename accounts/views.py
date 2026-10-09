from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .choices import ROLE_HR_ADMIN
from .decorators import block_demo_users, role_required
from .demo import DEMO_COMPANY_NAME, DEMO_USERS
from .forms import InvitationAcceptForm, InvitationForm, SignUpForm
from .selectors import invitation_get, invitation_get_by_token, invitation_list
from .services import (
    InvitationError,
    company_signup,
    invitation_accept,
    invitation_create,
    invitation_revoke,
)
from .tenancy import get_user_company


def signup_view(request):
    form = SignUpForm()

    if request.method == "POST":
        user, form = company_signup(data=request.POST)
        if user:
            login(request, user)
            return redirect("dashboard:home")

    return render(request, "accounts/signup.html", {"form": form})


@role_required(ROLE_HR_ADMIN)
@block_demo_users
def invitation_list_view(request):
    company = get_user_company(request.user)
    if company is None:
        raise PermissionDenied

    form = InvitationForm(company=company)

    if request.method == "POST":
        invitation, form = invitation_create(data=request.POST, user=request.user)
        if invitation:
            messages.success(request, f"Invite created for {invitation.email}. Copy the link below.")
            return redirect("accounts:invitation_list")

    invitations = [
        (
            invitation,
            request.build_absolute_uri(
                reverse("accounts:invitation_accept", args=[invitation.token])
            ),
        )
        for invitation in invitation_list(user=request.user)
    ]
    return render(
        request,
        "accounts/invitation_list.html",
        {"form": form, "invitations": invitations},
    )


@role_required(ROLE_HR_ADMIN)
@block_demo_users
def invitation_revoke_view(request, invitation_id):
    invitation = invitation_get(invitation_id, user=request.user)

    if request.method == "POST":
        invitation_revoke(invitation=invitation)
        messages.success(request, f"Invite for {invitation.email} revoked.")

    return redirect("accounts:invitation_list")


def invitation_accept_view(request, token):
    invitation = invitation_get_by_token(token)
    if not invitation.is_usable:
        return render(request, "accounts/invitation_invalid.html", status=410)

    form = InvitationAcceptForm()

    if request.method == "POST":
        try:
            user, form = invitation_accept(token=token, data=request.POST)
        except InvitationError:
            return render(request, "accounts/invitation_invalid.html", status=410)
        if user:
            login(request, user)
            messages.success(request, f"Welcome to {invitation.company.name}.")
            return redirect("dashboard:home")

    return render(
        request,
        "accounts/invitation_accept.html",
        {"form": form, "invitation": invitation},
    )


@require_POST
def demo_login_view(request, role):
    """One-click login for the public demo. Demo users have no usable password."""
    if not settings.DEMO_MODE or role not in DEMO_USERS:
        raise Http404
    user = get_object_or_404(
        get_user_model(),
        username=DEMO_USERS[role]["username"],
        profile__company__name=DEMO_COMPANY_NAME,
    )
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect("dashboard:home")
