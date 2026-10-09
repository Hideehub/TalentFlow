from .choices import DASHBOARD_ROLES, RECRUITMENT_ROLES, ROLE_HR_ADMIN
from .decorators import user_has_role
from .tenancy import get_user_company


def role_access(request):
    user_roles = []
    if request.user.is_authenticated:
        user_roles = list(request.user.groups.values_list("name", flat=True))
        if request.user.is_superuser and not user_roles:
            user_roles = ["Superuser"]

    return {
        "can_manage_recruitment": user_has_role(request.user, RECRUITMENT_ROLES),
        "can_view_reporting": user_has_role(request.user, DASHBOARD_ROLES),
        "can_manage_team": user_has_role(request.user, (ROLE_HR_ADMIN,)),
        "current_user_roles": user_roles,
        "current_company": get_user_company(request.user),
    }
