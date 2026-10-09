from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    demo_login_view,
    invitation_accept_view,
    invitation_list_view,
    invitation_revoke_view,
    signup_view,
)

app_name = "accounts"

urlpatterns = [
    path("signup/", signup_view, name="signup"),
    path("demo/<slug:role>/", demo_login_view, name="demo_login"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("invites/", invitation_list_view, name="invitation_list"),
    path(
        "invites/<int:invitation_id>/revoke/",
        invitation_revoke_view,
        name="invitation_revoke",
    ),
    path("invite/<str:token>/", invitation_accept_view, name="invitation_accept"),
]
