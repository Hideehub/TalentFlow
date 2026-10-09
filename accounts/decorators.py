from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .demo import is_demo_user
from .tenancy import get_user_company


def user_has_role(user, allowed_roles):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return user.groups.filter(name__in=allowed_roles).exists()


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            if not user_has_role(request.user, allowed_roles):
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


def company_required(redirect_to):
    """Send users with no company (e.g. a bare superuser) away instead of saving orphan rows."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if get_user_company(request.user) is None:
                messages.error(
                    request,
                    "Your account isn't linked to a company, so you can't do that here.",
                )
                return redirect(redirect_to)

            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


def block_demo_users(view_func):
    """Demo accounts may look around but not change shared, sensitive things (invites,
    resumes). Only writes are blocked; the matching forms are hidden in templates."""

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.method == "POST" and is_demo_user(request.user):
            raise PermissionDenied("This action is disabled for demo accounts.")
        return view_func(request, *args, **kwargs)

    return wrapped_view
