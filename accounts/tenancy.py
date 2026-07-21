from django.contrib.auth import get_user_model


def get_user_company(user):
    if not user or not user.is_authenticated:
        return None

    profile = getattr(user, "profile", None)
    return profile.company if profile else None


def company_users(user):
    company = get_user_company(user)
    if user and user.is_superuser:
        return get_user_model().objects.all()
    if not company:
        return get_user_model().objects.none()
    return get_user_model().objects.filter(profile__company=company)
