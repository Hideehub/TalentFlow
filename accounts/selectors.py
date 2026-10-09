from django.shortcuts import get_object_or_404

from .models import Invitation
from .tenancy import get_user_company


def invitation_list(*, user):
    return Invitation.objects.filter(
        company=get_user_company(user),
        accepted_at__isnull=True,
    ).select_related("invited_by")


def invitation_get(invitation_id, *, user):
    return get_object_or_404(invitation_list(user=user), id=invitation_id)


def invitation_get_by_token(token):
    return get_object_or_404(Invitation.objects.select_related("company"), token=token)
