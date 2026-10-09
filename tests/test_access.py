import pytest
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

from accounts.choices import ROLE_HIRING_MANAGER, ROLE_HR_ADMIN, ROLE_RECRUITER, SYSTEM_ROLES
from accounts.factories import CompanyFactory, UserFactory
from recruitment.factories import ApplicationFactory, CandidateFactory, JobOpeningFactory
from recruitment.selectors import application_scope, candidate_scope, job_opening_scope

pytestmark = pytest.mark.django_db


@pytest.fixture
def applications(company, recruiter, hiring_manager):
    """Applications in `company`: one per visibility case, all on jobs in that company."""
    other_recruiter = UserFactory(role=ROLE_RECRUITER, company=company)
    other_manager = UserFactory(role=ROLE_HIRING_MANAGER, company=company)
    managed_job = JobOpeningFactory(company=company, hiring_manager=hiring_manager)
    other_job = JobOpeningFactory(company=company, hiring_manager=other_manager)
    return {
        "mine": ApplicationFactory(job=other_job, assigned_recruiter=recruiter),
        "unassigned": ApplicationFactory(job=other_job),
        "theirs": ApplicationFactory(job=other_job, assigned_recruiter=other_recruiter),
        "managed": ApplicationFactory(job=managed_job, assigned_recruiter=other_recruiter),
    }


@pytest.fixture
def other_company_application():
    return ApplicationFactory()


# application_scope by role


def test_hr_admin_sees_all_company_applications(
    hr_admin, applications, other_company_application
):
    assert set(application_scope(hr_admin)) == set(applications.values())


def test_recruiter_sees_own_and_unassigned_applications(recruiter, applications):
    assert set(application_scope(recruiter)) == {
        applications["mine"],
        applications["unassigned"],
    }


def test_hiring_manager_sees_only_applications_for_their_jobs(hiring_manager, applications):
    assert set(application_scope(hiring_manager)) == {applications["managed"]}


def test_superuser_sees_every_companys_applications(applications, other_company_application):
    superuser = UserFactory(role="", company=False, is_superuser=True)

    assert set(application_scope(superuser)) == {
        *applications.values(),
        other_company_application,
    }


@pytest.mark.parametrize(
    "make_user",
    [
        lambda company: UserFactory(role="", company=company),
        lambda company: UserFactory(role=ROLE_HR_ADMIN, company=False),
        lambda company: AnonymousUser(),
    ],
    ids=["no-role", "no-company", "anonymous"],
)
def test_users_without_role_or_company_see_nothing(company, applications, make_user):
    user = make_user(company)

    assert not application_scope(user).exists()
    assert not candidate_scope(user).exists()


# candidate_scope by role


@pytest.mark.parametrize("user_fixture", ["hr_admin", "recruiter"])
def test_hr_admin_and_recruiter_see_every_company_candidate(
    request, user_fixture, applications, other_company_application
):
    user = request.getfixturevalue(user_fixture)
    unapplied = CandidateFactory(company=user.profile.company)

    expected = {application.candidate for application in applications.values()} | {unapplied}
    assert set(candidate_scope(user)) == expected


def test_recruiter_sees_person_but_not_their_hidden_applications(
    client, recruiter, applications
):
    # "theirs" belongs to another recruiter; give the same person an unassigned
    # application on a different job, which the recruiter can see.
    person = applications["theirs"].candidate
    visible = ApplicationFactory(candidate=person, job=JobOpeningFactory(company=person.company))
    client.force_login(recruiter)

    response = client.get(reverse("recruitment:candidate_detail", args=[person.id]))

    assert response.status_code == 200
    assert list(response.context["applications"]) == [visible]
    content = response.content.decode()
    assert reverse("recruitment:application_detail", args=[visible.id]) in content
    assert (
        reverse("recruitment:application_detail", args=[applications["theirs"].id])
        not in content
    )


def test_hiring_manager_sees_only_candidates_on_their_jobs(hiring_manager, applications):
    assert set(candidate_scope(hiring_manager)) == {applications["managed"].candidate}


# Company isolation


@pytest.mark.parametrize("role", SYSTEM_ROLES)
def test_user_never_sees_another_companys_data(role):
    user = UserFactory(role=role, company=CompanyFactory())
    other_application = ApplicationFactory(job__hiring_manager=user)

    assert other_application not in application_scope(user)
    assert other_application.candidate not in candidate_scope(user)
    assert other_application.job not in job_opening_scope(user)


def test_other_companys_detail_pages_return_404(client, hr_admin, other_company_application):
    client.force_login(hr_admin)

    urls = [
        reverse("recruitment:application_detail", args=[other_company_application.id]),
        reverse("recruitment:candidate_detail", args=[other_company_application.candidate.id]),
        reverse("recruitment:job_opening_detail", args=[other_company_application.job.id]),
    ]
    for url in urls:
        assert client.get(url).status_code == 404, url


def test_application_list_hides_other_companys_applications(
    client, hr_admin, applications, other_company_application
):
    client.force_login(hr_admin)

    response = client.get(reverse("recruitment:application_list"))

    assert set(response.context["applications"]) == set(applications.values())


# role_required


def test_anonymous_user_is_redirected_to_login(client):
    url = reverse("recruitment:candidate_list")

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"{reverse('accounts:login')}?next={url}"


def test_wrong_group_gets_403(client, hiring_manager):
    client.force_login(hiring_manager)

    assert client.get(reverse("recruitment:candidate_list")).status_code == 403


def test_allowed_group_gets_page(client, recruiter):
    client.force_login(recruiter)

    assert client.get(reverse("recruitment:candidate_list")).status_code == 200


def test_superuser_is_allowed_without_a_group(client):
    superuser = UserFactory(role="", company=False, is_superuser=True)
    client.force_login(superuser)

    assert client.get(reverse("recruitment:candidate_list")).status_code == 200
