import pytest
from django.urls import reverse

from recruitment.factories import ApplicationFactory, JobOpeningFactory
from recruitment.models import ApplicationNote, Interview

pytestmark = pytest.mark.django_db


@pytest.fixture
def managed_application(company, hiring_manager):
    job = JobOpeningFactory(company=company, hiring_manager=hiring_manager)
    return ApplicationFactory(job=job)


@pytest.fixture
def manager_client(client, hiring_manager):
    client.force_login(hiring_manager)
    return client


def test_hiring_manager_sees_application_read_only(manager_client, managed_application):
    response = manager_client.get(
        reverse("recruitment:application_detail", args=[managed_application.id])
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert reverse("recruitment:application_note_create", args=[managed_application.id]) in content
    assert reverse("recruitment:application_status_update", args=[managed_application.id]) not in content
    assert reverse("recruitment:interview_create", args=[managed_application.id]) not in content
    assert reverse("recruitment:application_update", args=[managed_application.id]) not in content


def test_hiring_manager_cannot_open_other_jobs_applications(manager_client, company):
    application = ApplicationFactory(job=JobOpeningFactory(company=company))

    response = manager_client.get(reverse("recruitment:application_detail", args=[application.id]))

    assert response.status_code == 404


def test_hiring_manager_can_add_a_note(manager_client, managed_application, hiring_manager):
    response = manager_client.post(
        reverse("recruitment:application_note_create", args=[managed_application.id]),
        {"note": "Strong system design answers."},
    )

    assert response.status_code == 302
    note = ApplicationNote.objects.get()
    assert note.application == managed_application
    assert note.author == hiring_manager


def test_note_author_is_shown_on_the_application(manager_client, managed_application, hiring_manager):
    hiring_manager.first_name, hiring_manager.last_name = "Hana", "Manager"
    hiring_manager.save()
    url = reverse("recruitment:application_detail", args=[managed_application.id])
    manager_client.post(
        reverse("recruitment:application_note_create", args=[managed_application.id]),
        {"note": "Strong system design answers."},
    )

    assert "Hana Manager" in manager_client.get(url).content.decode()


@pytest.mark.parametrize(
    ("url_name", "data"),
    [
        ("recruitment:application_status_update", {"status": "hired"}),
        ("recruitment:application_update", {}),
        ("recruitment:interview_create", {"title": "Onsite"}),
    ],
)
def test_hiring_manager_cannot_change_applications(
    manager_client, managed_application, url_name, data
):
    response = manager_client.post(reverse(url_name, args=[managed_application.id]), data)

    assert response.status_code == 403
    managed_application.refresh_from_db()
    assert managed_application.status == "applied"
    assert not Interview.objects.exists()


def test_hiring_manager_cannot_open_candidate_profile(manager_client, managed_application):
    url = reverse("recruitment:candidate_detail", args=[managed_application.candidate.id])

    assert manager_client.get(url).status_code == 403
