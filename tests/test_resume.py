from datetime import timedelta

import pytest
from django.conf import settings
from django.core.files.storage import FileSystemStorage, storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from accounts.choices import ROLE_HIRING_MANAGER, ROLE_HR_ADMIN, ROLE_RECRUITER
from accounts.factories import UserFactory
from recruitment.factories import ApplicationFactory, CandidateFactory, JobOpeningFactory
from recruitment.forms import MAX_RESUME_SIZE
from recruitment.models import Candidate, Interview, resume_storage

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.7\n fake resume body"


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    """Keep test uploads out of the real private_media/ folder."""
    test_storage = FileSystemStorage(location=tmp_path)
    monkeypatch.setattr(Candidate._meta.get_field("resume"), "storage", test_storage)
    return test_storage


@pytest.fixture
def application(company, hiring_manager):
    return ApplicationFactory(job=JobOpeningFactory(company=company, hiring_manager=hiring_manager))


@pytest.fixture
def candidate(application):
    return application.candidate


def upload(client, candidate, name="My CV.pdf", content=PDF):
    return client.post(
        reverse("recruitment:candidate_resume_upload", args=[candidate.id]),
        {"resume": SimpleUploadedFile(name, content)},
    )


@pytest.fixture
def uploaded(client, hr_admin, candidate):
    client.force_login(hr_admin)
    upload(client, candidate)
    candidate.refresh_from_db()
    client.logout()
    return candidate


# Upload


def test_upload_stores_file_under_a_random_name(client, hr_admin, candidate, storage):
    client.force_login(hr_admin)

    response = upload(client, candidate)

    assert response.status_code == 302
    candidate.refresh_from_db()
    assert candidate.resume.name.startswith(f"resumes/{candidate.company_id}/{candidate.id}/")
    assert "CV" not in candidate.resume.name
    assert candidate.resume_original_name == "My CV.pdf"
    assert timezone.now() - candidate.resume_uploaded_at < timedelta(minutes=1)
    with storage.open(candidate.resume.name) as stored:
        assert stored.read() == PDF


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("cv.exe", PDF),
        ("cv.pdf", b"MZ not really a pdf"),
        ("cv.docx", PDF),
        ("cv.pdf", b"%PDF-" + b"x" * MAX_RESUME_SIZE),
    ],
    ids=["bad-extension", "bad-content", "pdf-renamed-docx", "too-big"],
)
def test_invalid_resumes_are_rejected(client, hr_admin, candidate, name, content):
    client.force_login(hr_admin)

    upload(client, candidate, name=name, content=content)

    candidate.refresh_from_db()
    assert not candidate.resume


def test_docx_with_zip_signature_is_accepted(client, hr_admin, candidate):
    client.force_login(hr_admin)

    upload(client, candidate, name="cv.docx", content=b"PK\x03\x04 rest of docx")

    candidate.refresh_from_db()
    assert candidate.resume_original_name == "cv.docx"


def test_replacing_deletes_the_old_file_after_commit(
    client, hr_admin, uploaded, storage, django_capture_on_commit_callbacks
):
    old_name = uploaded.resume.name
    client.force_login(hr_admin)

    with django_capture_on_commit_callbacks(execute=True):
        upload(client, uploaded, name="new.pdf")

    uploaded.refresh_from_db()
    assert uploaded.resume.name != old_name
    assert not storage.exists(old_name)
    assert storage.exists(uploaded.resume.name)


def test_hiring_manager_cannot_upload(client, hiring_manager, candidate):
    client.force_login(hiring_manager)

    assert upload(client, candidate).status_code == 403


def test_profile_shows_upload_date(client, hr_admin, uploaded):
    client.force_login(hr_admin)

    page = client.get(reverse("recruitment:candidate_detail", args=[uploaded.id]))

    assert "My CV.pdf" in page.content.decode()
    assert "Uploaded" in page.content.decode()


# Download is scoped


def download(client, candidate):
    return client.get(reverse("recruitment:candidate_resume", args=[candidate.id]))


@pytest.mark.parametrize("user_fixture", ["hr_admin", "recruiter", "hiring_manager"])
def test_users_in_scope_can_download(client, request, uploaded, user_fixture):
    client.force_login(request.getfixturevalue(user_fixture))

    response = download(client, uploaded)

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == PDF
    assert response["Content-Disposition"].startswith("attachment")
    assert "My CV.pdf" in response["Content-Disposition"]
    assert response["X-Content-Type-Options"] == "nosniff"


def test_interviewer_can_download(client, uploaded, application, company):
    interviewer = UserFactory(role=ROLE_HIRING_MANAGER, company=company)
    Interview.objects.create(
        application=application, title="Tech", scheduled_at=timezone.now(), interviewer=interviewer
    )
    client.force_login(interviewer)

    assert download(client, uploaded).status_code == 200


@pytest.mark.parametrize(
    "make_user",
    [
        lambda company: UserFactory(role=ROLE_HIRING_MANAGER, company=company),
        lambda company: UserFactory(role=ROLE_HR_ADMIN),
    ],
    ids=["manager-of-another-job", "other-company"],
)
def test_users_out_of_scope_get_404(client, uploaded, company, make_user):
    client.force_login(make_user(company))

    assert download(client, uploaded).status_code == 404


# Recruiters need an application they can see


def test_recruiter_cannot_download_when_application_belongs_to_another_recruiter(
    client, recruiter, uploaded, application, company
):
    application.assigned_recruiter = UserFactory(role=ROLE_RECRUITER, company=company)
    application.save()
    client.force_login(recruiter)

    assert download(client, uploaded).status_code == 404
    page = client.get(reverse("recruitment:candidate_detail", args=[uploaded.id]))
    assert page.status_code == 200
    download_link = f'href="{reverse("recruitment:candidate_resume", args=[uploaded.id])}"'
    assert download_link not in page.content.decode()
    assert "Resume on file" in page.content.decode()


def test_recruiter_can_download_for_own_application(client, recruiter, uploaded, application):
    application.assigned_recruiter = recruiter
    application.save()
    client.force_login(recruiter)

    assert download(client, uploaded).status_code == 200


def test_recruiter_interviewer_can_download(client, uploaded, application, company):
    application.assigned_recruiter = UserFactory(role=ROLE_RECRUITER, company=company)
    application.save()
    interviewer = UserFactory(role=ROLE_RECRUITER, company=company)
    Interview.objects.create(
        application=application, title="Tech", scheduled_at=timezone.now(), interviewer=interviewer
    )
    client.force_login(interviewer)

    assert download(client, uploaded).status_code == 200


def test_candidate_without_applications_only_hr_admin_can_download(
    client, hr_admin, recruiter, company
):
    candidate = CandidateFactory(company=company)
    client.force_login(hr_admin)
    upload(client, candidate)

    assert download(client, candidate).status_code == 200
    client.force_login(recruiter)
    assert download(client, candidate).status_code == 404


def test_anonymous_is_sent_to_login(client, uploaded):
    response = download(client, uploaded)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_no_resume_returns_404(client, hr_admin, candidate):
    client.force_login(hr_admin)

    assert download(client, candidate).status_code == 404


# Never public


def test_resume_files_have_no_public_url(client, hr_admin, uploaded):
    client.force_login(hr_admin)

    for prefix in ("/private_media/", "/media/", "/"):
        assert client.get(prefix + uploaded.resume.name).status_code == 404


def test_field_uses_the_configured_private_storage():
    assert resume_storage() is storages["resumes"]
    assert storages["resumes"].location == str(settings.PRIVATE_MEDIA_ROOT)
