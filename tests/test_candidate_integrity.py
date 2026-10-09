import pytest
from django.db import IntegrityError, transaction

from accounts.choices import ROLE_HIRING_MANAGER
from accounts.factories import UserFactory
from recruitment.factories import ApplicationFactory, CandidateFactory, JobOpeningFactory
from recruitment.models import Application, Candidate, JobOpening
from recruitment.services import (
    CANDIDATE_JUST_ADDED,
    application_create,
    candidate_create,
    candidate_update,
    interview_create,
    job_opening_create,
    job_opening_update,
)

pytestmark = pytest.mark.django_db


def candidate_data(job, **overrides):
    data = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "phone": "08000000000",
        "years_of_experience": 3,
        "source": "referral",
        "application-job": job.id,
        "application-status": "applied",
    }
    data.update(overrides)
    return data


@pytest.fixture
def job(company):
    return JobOpeningFactory(company=company)


# Creating a candidate with their first application


def test_candidate_create_makes_person_and_first_application(recruiter, job, company):
    candidate, created, candidate_form, application_form = candidate_create(
        data=candidate_data(job), user=recruiter
    )

    assert candidate is not None, (candidate_form.errors, application_form.errors)
    assert created is True
    assert candidate.company == company
    application = candidate.applications.get()
    assert application.job == job
    assert application.assigned_recruiter == recruiter


def test_candidate_create_saves_nothing_if_application_is_invalid(recruiter, job):
    candidate, _created, _candidate_form, application_form = candidate_create(
        data=candidate_data(job, **{"application-job": ""}), user=recruiter
    )

    assert candidate is None
    assert "job" in application_form.errors
    assert not Candidate.objects.exists()


def test_candidate_form_lowercases_email(recruiter, job):
    candidate, *_forms = candidate_create(
        data=candidate_data(job, email="  Ada@Example.COM "), user=recruiter
    )

    assert candidate.email == "ada@example.com"


def test_existing_email_in_any_case_adds_application_to_existing_person(
    recruiter, job, company
):
    existing = CandidateFactory(company=company, email="ada@example.com", full_name="Ada L.")

    candidate, created, _candidate_form, _application_form = candidate_create(
        data=candidate_data(job, email="ADA@example.com", full_name="Someone Else"),
        user=recruiter,
    )

    assert candidate == existing
    assert created is False
    assert Candidate.objects.count() == 1
    existing.refresh_from_db()
    assert existing.full_name == "Ada L."
    assert existing.applications.get().job == job


def test_existing_person_already_applied_to_same_job_is_a_form_error(recruiter, job, company):
    existing = CandidateFactory(company=company, email="ada@example.com")
    ApplicationFactory(candidate=existing, job=job)

    candidate, _created, _candidate_form, application_form = candidate_create(
        data=candidate_data(job, email="Ada@example.com"), user=recruiter
    )

    assert candidate is None
    assert application_form.errors["job"] == ["Already applied — unassigned."]
    assert existing.applications.count() == 1


def test_already_applied_error_names_the_owning_recruiter(hr_admin, job, company):
    owner = UserFactory(company=company, first_name="Jane", last_name="Smith")
    existing = ApplicationFactory(job=job, assigned_recruiter=owner)

    application, form = application_create(
        candidate=existing.candidate, data={"job": job.id, "status": "applied"}, user=hr_admin
    )

    assert application is None
    assert form.errors["job"] == ["Already applied — owned by Jane Smith."]


def test_simultaneous_new_email_shows_form_error(recruiter, job, company, monkeypatch):
    # Simulate losing the race: the lookup misses, then the insert hits the constraint.
    CandidateFactory(company=company, email="ada@example.com")
    monkeypatch.setattr("recruitment.services._find_candidate", lambda company, email: None)

    candidate, created, candidate_form, _application_form = candidate_create(
        data=candidate_data(job), user=recruiter
    )

    assert candidate is None
    assert created is False
    assert candidate_form.errors["email"] == [CANDIDATE_JUST_ADDED]
    assert Candidate.objects.count() == 1
    assert not Application.objects.exists()


def test_editing_a_candidate_to_another_persons_email_is_a_form_error(company):
    CandidateFactory(company=company, email="ada@example.com")
    candidate = CandidateFactory(company=company, email="grace@example.com")
    data = {
        "full_name": "Grace",
        "email": "ADA@example.com",
        "phone": "1",
        "years_of_experience": 3,
        "source": "other",
    }

    updated, form = candidate_update(candidate=candidate, data=data)

    assert updated is None
    assert "email" in form.errors


def test_same_email_is_allowed_in_another_company(recruiter, job):
    CandidateFactory(email="ada@example.com")

    candidate, *_forms = candidate_create(data=candidate_data(job), user=recruiter)

    assert candidate is not None


def test_editing_a_candidate_keeps_its_own_email(company):
    candidate = CandidateFactory(company=company, email="ada@example.com")
    data = {
        "full_name": "Ada L.",
        "email": "ada@example.com",
        "phone": "1",
        "years_of_experience": 3,
        "source": "other",
    }

    updated, form = candidate_update(candidate=candidate, data=data)

    assert updated is not None, form.errors


# Applications


def test_second_application_to_same_job_is_a_form_error(hr_admin, job):
    existing = ApplicationFactory(job=job)

    application, form = application_create(
        candidate=existing.candidate, data={"job": job.id, "status": "applied"}, user=hr_admin
    )

    assert application is None
    assert "job" in form.errors


def test_same_candidate_can_apply_to_another_job(hr_admin, job, company):
    existing = ApplicationFactory(job=job)
    other_job = JobOpeningFactory(company=company)

    application, form = application_create(
        candidate=existing.candidate, data={"job": other_job.id, "status": "applied"}, user=hr_admin
    )

    assert application is not None, form.errors


def test_application_cannot_use_another_companys_job(hr_admin, company):
    candidate = CandidateFactory(company=company)
    foreign_job = JobOpeningFactory()

    application, form = application_create(
        candidate=candidate, data={"job": foreign_job.id, "status": "applied"}, user=hr_admin
    )

    assert application is None
    assert "job" in form.errors


# Interviews and hiring managers


def test_interviewer_must_be_a_company_user(hr_admin, recruiter, job):
    application = ApplicationFactory(job=job)
    outsider = UserFactory()
    data = {"title": "Onsite", "scheduled_at": "2026-11-02T10:00", "status": "scheduled"}

    interview, _form = interview_create(application=application, data={**data, "interviewer": recruiter.id})
    rejected, form = interview_create(application=application, data={**data, "interviewer": outsider.id})

    assert interview.interviewer == recruiter
    assert rejected is None
    assert "interviewer" in form.errors


def test_hiring_manager_must_be_a_company_hiring_manager(hr_admin, hiring_manager, recruiter):
    outsider_manager = UserFactory(role=ROLE_HIRING_MANAGER)
    base = {"title": "Dev", "department": "Engineering", "employment_type": "full_time"}

    job, _form = job_opening_create(data={**base, "hiring_manager": hiring_manager.id}, user=hr_admin)
    for not_allowed in (recruiter, outsider_manager):
        rejected, form = job_opening_create(
            data={**base, "hiring_manager": not_allowed.id}, user=hr_admin
        )
        assert rejected is None
        assert "hiring_manager" in form.errors

    assert job.hiring_manager == hiring_manager


def test_renamed_job_shows_on_applications_without_syncing(hr_admin, job):
    application = ApplicationFactory(job=job)
    data = {
        "title": "Renamed",
        "department": job.department,
        "employment_type": job.employment_type,
        "status": job.status,
    }

    updated, form = job_opening_update(job=job, data=data, user=hr_admin)

    assert updated is not None, form.errors
    application.refresh_from_db()
    assert application.position == "Renamed"


# Database constraints


def test_database_rejects_case_insensitive_duplicate_candidate(company):
    CandidateFactory(company=company, email="ada@example.com")

    with pytest.raises(IntegrityError), transaction.atomic():
        CandidateFactory(company=company, email="ADA@example.com")


def test_database_rejects_duplicate_application_for_same_job(job):
    existing = ApplicationFactory(job=job)

    with pytest.raises(IntegrityError), transaction.atomic():
        Application.objects.create(candidate=existing.candidate, job=job)


def test_database_rejects_duplicate_imported_position_without_job(company):
    candidate = CandidateFactory(company=company)
    ApplicationFactory(candidate=candidate, job=None, imported_position="Data Wizard")

    with pytest.raises(IntegrityError), transaction.atomic():
        ApplicationFactory(candidate=candidate, job=None, imported_position="DATA WIZARD")


def test_imported_position_rule_ignores_other_positions_and_applications_with_jobs(job):
    application = ApplicationFactory(job=job, imported_position="Backend")

    ApplicationFactory(candidate=application.candidate, job=None, imported_position="Backend")
    ApplicationFactory(candidate=application.candidate, job=None, imported_position="Frontend")

    assert application.candidate.applications.count() == 3


def test_candidate_requires_a_company():
    with pytest.raises(IntegrityError), transaction.atomic():
        Candidate.objects.create(full_name="Ada", email="ada@example.com", phone="1")


def test_job_opening_requires_a_company():
    with pytest.raises(IntegrityError), transaction.atomic():
        JobOpening.objects.create(title="Dev", department="Engineering")
