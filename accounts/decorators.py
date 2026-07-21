from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


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
