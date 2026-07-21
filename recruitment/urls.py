from django.urls import path

from . import views

app_name = "recruitment"

urlpatterns = [
    path("", views.candidate_list_view, name="candidate_list"),
    path("jobs/", views.job_opening_list_view, name="job_opening_list"),
    path("jobs/new/", views.job_opening_create_view, name="job_opening_create"),
    path("jobs/<uuid:job_id>/", views.job_opening_detail_view, name="job_opening_detail"),
    path("jobs/<uuid:job_id>/edit/", views.job_opening_update_view, name="job_opening_update"),
    path("candidates/new/", views.candidate_create_view, name="candidate_create"),
    path("candidates/<uuid:candidate_id>/", views.candidate_detail_view, name="candidate_detail"),
    path("candidates/<uuid:candidate_id>/edit/", views.candidate_update_view, name="candidate_update"),
    path("candidates/<uuid:candidate_id>/status/", views.candidate_status_update_view, name="candidate_status_update"),
    path("candidates/<uuid:candidate_id>/notes/", views.candidate_note_create_view, name="candidate_note_create"),
    path("candidates/<uuid:candidate_id>/interviews/", views.interview_create_view, name="interview_create"),
]
