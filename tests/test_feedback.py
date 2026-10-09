from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.choices import ROLE_HIRING_MANAGER, ROLE_RECRUITER
from accounts.factories import UserFactory
from recruitment.factories import ApplicationFactory, JobOpeningFactory
from recruitment.models import Interview, InterviewFeedback
from dashboard.selectors import dashboard_summary
from recruitment.selectors import application_feedback
from reports.selectors import recruitment_summary_report
from recruitment.services import interview_feedback_submit

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(company, recruiter, hiring_manager, hr_admin):
    """An application owned by `recruiter` on a job managed by `hiring_manager`, with two
    interviewers who otherwise couldn't see it: another recruiter and another manager."""
    job = JobOpeningFactory(company=company, hiring_manager=hiring_manager)
    application = ApplicationFactory(job=job, assigned_recruiter=recruiter)
    recruiter_interviewer = UserFactory(role=ROLE_RECRUITER, company=company)
    manager_interviewer = UserFactory(role=ROLE_HIRING_MANAGER, company=company)
    past = timezone.now() - timedelta(hours=1)
    first = Interview.objects.create(
        application=application, title="Tech", scheduled_at=past, interviewer=recruiter_interviewer
    )
    second = Interview.objects.create(
        application=application, title="Culture", scheduled_at=past, interviewer=manager_interviewer
    )
    return {
        "application": application,
        "first": first,
        "second": second,
        "recruiter_interviewer": recruiter_interviewer,
        "manager_interviewer": manager_interviewer,
    }


def give(interview, user, recommendation="yes", comments="Solid."):
    feedback, form = interview_feedback_submit(
        interview=interview,
        data={"recommendation": recommendation, "comments": comments},
        user=user,
    )
    assert feedback is not None, form.errors
    return feedback


# Interviewers can read the application, but not change it


@pytest.mark.parametrize("interviewer", ["recruiter_interviewer", "manager_interviewer"])
def test_interviewer_can_view_the_application_read_only(client, setup, interviewer):
    application = setup["application"]
    client.force_login(setup[interviewer])

    page = client.get(reverse("recruitment:application_detail", args=[application.id]))

    assert page.status_code == 200
    content = page.content.decode()
    for url_name in (
        "recruitment:application_status_update",
        "recruitment:application_note_create",
        "recruitment:interview_create",
        "recruitment:application_update",
    ):
        assert reverse(url_name, args=[application.id]) not in content


def test_interviewer_cannot_change_status_or_add_notes(client, setup):
    application = setup["application"]
    client.force_login(setup["recruiter_interviewer"])

    status = client.post(
        reverse("recruitment:application_status_update", args=[application.id]),
        {"status": "hired"},
    )
    note = client.post(
        reverse("recruitment:application_note_create", args=[application.id]), {"note": "Hi"}
    )

    assert (status.status_code, note.status_code) == (404, 404)
    application.refresh_from_db()
    assert application.status == "applied"


def test_recruiter_who_is_not_owner_or_interviewer_cannot_view(client, setup, company):
    client.force_login(UserFactory(role=ROLE_RECRUITER, company=company))

    response = client.get(reverse("recruitment:application_detail", args=[setup["application"].id]))

    assert response.status_code == 404


# Submitting feedback


def test_only_the_assigned_interviewer_can_open_the_feedback_form(
    client, setup, recruiter, hr_admin
):
    url = reverse("recruitment:interview_feedback", args=[setup["first"].id])

    for user in (setup["manager_interviewer"], recruiter, hr_admin):
        client.force_login(user)
        assert client.get(url).status_code == 404

    client.force_login(setup["recruiter_interviewer"])
    assert client.get(url).status_code == 200


def test_submitting_again_edits_the_same_feedback(client, setup):
    interviewer = setup["recruiter_interviewer"]
    url = reverse("recruitment:interview_feedback", args=[setup["first"].id])
    client.force_login(interviewer)

    client.post(url, {"recommendation": "yes", "comments": "Good."})
    response = client.post(url, {"recommendation": "strong_no", "comments": "Changed my mind."})

    assert response.status_code == 302
    feedback = InterviewFeedback.objects.get()
    assert (feedback.author, feedback.recommendation, feedback.comments) == (
        interviewer,
        "strong_no",
        "Changed my mind.",
    )


# Who can read feedback


def test_interviewer_sees_others_feedback_only_after_submitting_their_own(setup):
    application = setup["application"]
    other = give(setup["second"], setup["manager_interviewer"])

    assert list(application_feedback(application, user=setup["recruiter_interviewer"])) == []

    mine = give(setup["first"], setup["recruiter_interviewer"])

    assert set(application_feedback(application, user=setup["recruiter_interviewer"])) == {
        mine,
        other,
    }


@pytest.mark.parametrize("viewer", ["hr_admin", "recruiter", "hiring_manager"])
def test_hr_admin_owner_and_job_manager_see_all_feedback(request, setup, viewer):
    give(setup["first"], setup["recruiter_interviewer"])
    give(setup["second"], setup["manager_interviewer"])

    user = request.getfixturevalue(viewer)

    assert application_feedback(setup["application"], user=user).count() == 2


def test_other_recruiter_on_unassigned_application_sees_no_feedback(setup, company):
    application = setup["application"]
    application.assigned_recruiter = None
    application.save()
    give(setup["first"], setup["recruiter_interviewer"])
    other_recruiter = UserFactory(role=ROLE_RECRUITER, company=company)

    assert not application_feedback(application, user=other_recruiter).exists()


def test_hidden_feedback_is_not_in_the_page(client, setup):
    give(setup["second"], setup["manager_interviewer"], comments="Secret opinion.")
    client.force_login(setup["recruiter_interviewer"])
    url = reverse("recruitment:application_detail", args=[setup["application"].id])

    assert "Secret opinion." not in client.get(url).content.decode()

    give(setup["first"], setup["recruiter_interviewer"])

    assert "Secret opinion." in client.get(url).content.decode()


def test_dashboard_lists_interviews_awaiting_my_feedback(client, setup):
    client.force_login(setup["recruiter_interviewer"])
    feedback_url = reverse("recruitment:interview_feedback", args=[setup["first"].id])

    assert feedback_url in client.get(reverse("dashboard:home")).content.decode()

    give(setup["first"], setup["recruiter_interviewer"])

    assert feedback_url not in client.get(reverse("dashboard:home")).content.decode()


@pytest.mark.parametrize("interviewer", ["recruiter_interviewer", "manager_interviewer"])
def test_interview_only_applications_are_not_in_dashboard_or_report_numbers(
    setup, recruiter, interviewer
):
    user = setup[interviewer]

    assert dashboard_summary(user)["candidate_count"] == 0
    assert recruitment_summary_report(user)["total_candidates"] == 0
    assert dashboard_summary(recruiter)["candidate_count"] == 1
