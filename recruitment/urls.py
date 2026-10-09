from django.urls import path

from . import views

app_name = "recruitment"

urlpatterns = [
    path("", views.application_list_view, name="application_list"),
    path("jobs/", views.job_opening_list_view, name="job_opening_list"),
    path("jobs/new/", views.job_opening_create_view, name="job_opening_create"),
    path("jobs/<uuid:job_id>/", views.job_opening_detail_view, name="job_opening_detail"),
    path("jobs/<uuid:job_id>/edit/", views.job_opening_update_view, name="job_opening_update"),
    path("candidates/", views.candidate_list_view, name="candidate_list"),
    path("candidates/new/", views.candidate_create_view, name="candidate_create"),
    path("candidates/<uuid:candidate_id>/", views.candidate_detail_view, name="candidate_detail"),
    path("candidates/<uuid:candidate_id>/edit/", views.candidate_update_view, name="candidate_update"),
    path("candidates/<uuid:candidate_id>/applications/new/", views.application_create_view, name="application_create"),
    path("candidates/<uuid:candidate_id>/resume/", views.candidate_resume_download_view, name="candidate_resume"),
    path("candidates/<uuid:candidate_id>/resume/upload/", views.candidate_resume_upload_view, name="candidate_resume_upload"),
    path("applications/<uuid:application_id>/", views.application_detail_view, name="application_detail"),
    path("applications/<uuid:application_id>/edit/", views.application_update_view, name="application_update"),
    path("applications/<uuid:application_id>/status/", views.application_status_update_view, name="application_status_update"),
    path("applications/<uuid:application_id>/notes/", views.application_note_create_view, name="application_note_create"),
    path("applications/<uuid:application_id>/interviews/", views.interview_create_view, name="interview_create"),
    path("interviews/<uuid:interview_id>/feedback/", views.interview_feedback_view, name="interview_feedback"),
]
