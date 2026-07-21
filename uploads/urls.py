from django.urls import path

from . import views

app_name = "uploads"

urlpatterns = [
    path("candidates/", views.candidate_import_view, name="candidate_import"),
    path("candidates/confirm/", views.candidate_import_confirm_view, name="candidate_import_confirm"),
]
