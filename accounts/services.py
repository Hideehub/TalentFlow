from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.utils import timezone

from .choices import ROLE_HR_ADMIN
from .forms import COMPANY_NAME_TAKEN, InvitationAcceptForm, InvitationForm, SignUpForm
from .models import Company, Invitation, UserProfile
from .tenancy import get_user_company


class InvitationError(Exception):
    pass


def _join_company(user, *, company, role):
    UserProfile.objects.create(user=user, company=company)
    group, _created = Group.objects.get_or_create(name=role)
    user.groups.add(group)


@transaction.atomic
def company_signup(*, data):
    form = SignUpForm(data=data)
    if form.is_valid():
        # The form already checked the name, but a simultaneous signup can still win the
        # race. The savepoint keeps the outer transaction usable after the IntegrityError.
        try:
            with transaction.atomic():
                company = Company.objects.create(name=form.cleaned_data["company_name"])
        except IntegrityError:
            form.add_error("company_name", COMPANY_NAME_TAKEN)
            return None, form
        user = form.save()
        _join_company(user, company=company, role=ROLE_HR_ADMIN)
        return user, form
    return None, form


@transaction.atomic
def invitation_create(*, data, user):
    company = get_user_company(user)
    form = InvitationForm(data=data, company=company)
    if form.is_valid():
        invitation = form.save(commit=False)
        invitation.company = company
        invitation.invited_by = user
        invitation.save()
        return invitation, form
    return None, form


@transaction.atomic
def invitation_revoke(*, invitation):
    invitation.delete()


@transaction.atomic
def invitation_accept(*, token, data):
    # Lock the invite row so two concurrent submits can't both accept it.
    invitation = Invitation.objects.select_for_update().filter(token=token).first()
    if invitation is None or not invitation.is_usable:
        raise InvitationError("This invite is no longer valid.")

    form = InvitationAcceptForm(data=data)
    if form.is_valid():
        user = form.save(commit=False)
        user.email = invitation.email
        user.save()
        _join_company(user, company=invitation.company, role=invitation.role)
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at"])
        return user, form
    return None, form
