from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook

from recruitment.factories import ApplicationFactory, CandidateFactory, JobOpeningFactory
from recruitment.models import Application, Candidate
from uploads.services import candidate_import_confirm, candidate_import_preview

pytestmark = pytest.mark.django_db

HEADER = ["Applicant Name", "Email", "Phone", "Position", "Experience", "Stage"]


def xlsx(*rows, header=HEADER):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile(
        "candidates.xlsx",
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def run_import(user, *rows, assigned_recruiter=None, header=HEADER):
    preview = candidate_import_preview(xlsx(*rows, header=header), user=user)
    result = candidate_import_confirm(
        preview["rows"], user=user, assigned_recruiter=assigned_recruiter
    )
    return preview, result


@pytest.fixture
def job(company):
    return JobOpeningFactory(company=company, title="Backend Engineer")


def test_row_matching_an_open_job_creates_candidate_and_application(hr_admin, company, job):
    _preview, result = run_import(
        hr_admin, ("ADA LOVELACE", "Ada@Example.com", "0800", "backend engineer", 3, "Screening")
    )

    assert result == {"imported": 1, "new_candidates": 1, "skipped": 0}
    candidate = Candidate.objects.get()
    assert (candidate.company, candidate.full_name, candidate.email) == (
        company,
        "Ada Lovelace",
        "ada@example.com",
    )
    assert candidate.source == "import"
    application = candidate.applications.get()
    assert (application.job, application.imported_position, application.status) == (
        job,
        "",
        "screening",
    )


def test_row_without_matching_job_keeps_imported_position(hr_admin):
    run_import(hr_admin, ("Ada", "ada@example.com", "0800", "Data Wizard", 3, "applied"))

    application = Application.objects.get()
    assert application.job is None
    assert application.imported_position == "Data Wizard"


def test_existing_candidate_gets_a_new_application(hr_admin, company, job):
    existing = CandidateFactory(company=company, email="ada@example.com", full_name="Ada L.")

    preview, result = run_import(
        hr_admin, ("Someone Else", "ADA@example.com", "0800", "Backend Engineer", 3, "applied")
    )

    assert preview["rows"][0]["existing_candidate"] is True
    assert result == {"imported": 1, "new_candidates": 0, "skipped": 0}
    assert Candidate.objects.count() == 1
    existing.refresh_from_db()
    assert existing.full_name == "Ada L."
    assert existing.applications.get().job == job


@pytest.mark.parametrize("position", ["Backend Engineer", "Data Wizard"])
def test_existing_application_for_same_position_is_flagged_and_skipped(
    hr_admin, company, job, position
):
    candidate = CandidateFactory(company=company, email="ada@example.com")
    if position == job.title:
        ApplicationFactory(candidate=candidate, job=job)
    else:
        ApplicationFactory(candidate=candidate, job=None, imported_position=position)

    preview, result = run_import(
        hr_admin, ("Ada", "ada@example.com", "0800", position.upper(), 3, "applied")
    )

    assert "already has an application" in " ".join(preview["rows"][0]["errors"])
    assert result["imported"] == 0
    assert Application.objects.count() == 1


def test_confirm_rechecks_applications_created_after_preview(hr_admin, company, job):
    preview = candidate_import_preview(
        xlsx(("Ada", "ada@example.com", "0800", "Backend Engineer", 3, "applied")), user=hr_admin
    )
    ApplicationFactory(candidate=CandidateFactory(company=company, email="ada@example.com"), job=job)

    result = candidate_import_confirm(preview["rows"], user=hr_admin)

    assert result == {"imported": 0, "new_candidates": 0, "skipped": 1}


def test_same_email_in_another_company_is_a_new_candidate(hr_admin, company):
    CandidateFactory(email="ada@example.com")

    preview, result = run_import(
        hr_admin, ("Ada", "ada@example.com", "0800", "Data Wizard", 3, "applied")
    )

    assert preview["rows"][0]["existing_candidate"] is False
    assert result["new_candidates"] == 1
    assert Candidate.objects.filter(company=company).count() == 1


def test_same_email_with_different_positions_is_one_candidate_with_two_applications(
    hr_admin, job
):
    preview, result = run_import(
        hr_admin,
        ("Ada", "ada@example.com", "0800", "Backend Engineer", 3, "applied"),
        ("Ada", "ADA@example.com", "0800", "Data Wizard", 3, "screening"),
    )

    assert preview["valid_rows"] == 2
    assert result == {"imported": 2, "new_candidates": 1, "skipped": 0}
    candidate = Candidate.objects.get()
    assert {application.position for application in candidate.applications.all()} == {
        "Backend Engineer",
        "Data Wizard",
    }


def test_same_email_and_same_position_in_file_is_an_error(hr_admin):
    preview, result = run_import(
        hr_admin,
        ("Ada", "ada@example.com", "0800", "Data Wizard", 3, "applied"),
        ("Ada", "ada@example.com", "0800", "data wizard", 3, "applied"),
    )

    assert [row["is_valid"] for row in preview["rows"]] == [False, False]
    assert "more than once" in " ".join(preview["rows"][0]["errors"])
    assert result["imported"] == 0
    assert not Candidate.objects.exists()


def test_invalid_rows_are_reported_and_not_imported(hr_admin):
    preview, result = run_import(
        hr_admin,
        ("Ada", "ada@example.com", "0800", "Data Wizard", 3, "applied"),
        ("", "not-an-email", "0800", "Data Wizard", 3, "applied"),
        ("Grace", "grace@example.com", "0800", "Data Wizard", 3, "daydreaming"),
    )

    assert [row["is_valid"] for row in preview["rows"]] == [True, False, False]
    assert result["imported"] == 1
    assert Candidate.objects.get().email == "ada@example.com"


def test_import_through_views_assigns_the_recruiter(client, recruiter, job):
    client.force_login(recruiter)
    upload = xlsx(("Ada", "ada@example.com", "0800", "Backend Engineer", 3, "applied"))

    client.post(reverse("uploads:candidate_import"), {"file": upload})
    response = client.post(reverse("uploads:candidate_import_confirm"))

    assert response.status_code == 302
    assert response.url == reverse("recruitment:application_list")
    assert Application.objects.get().assigned_recruiter == recruiter


# Optional Source column

SOURCE_HEADER = [*HEADER, "Source"]


def test_source_column_sets_new_candidates_source(hr_admin):
    preview, _result = run_import(
        hr_admin,
        ("Ada", "ada@example.com", "0800", "Data Wizard", 3, "applied", "LinkedIn"),
        ("Grace", "grace@example.com", "0800", "Data Wizard", 3, "applied", "job board"),
        ("Alan", "alan@example.com", "0800", "Data Wizard", 3, "applied", ""),
        header=SOURCE_HEADER,
    )

    assert [row["source_label"] for row in preview["rows"]] == ["LinkedIn", "Job board", "Excel import"]
    assert dict(Candidate.objects.values_list("email", "source")) == {
        "ada@example.com": "linkedin",
        "grace@example.com": "job_board",
        "alan@example.com": "import",
    }


def test_unknown_source_is_a_row_error(hr_admin):
    preview, result = run_import(
        hr_admin,
        ("Ada", "ada@example.com", "0800", "Data Wizard", 3, "applied", "Carrier pigeon"),
        header=SOURCE_HEADER,
    )

    assert "Source is not recognized." in preview["rows"][0]["errors"]
    assert result["imported"] == 0


def test_source_column_does_not_change_an_existing_person(hr_admin, company):
    existing = CandidateFactory(company=company, email="ada@example.com", source="referral")

    run_import(
        hr_admin,
        ("Ada", "ada@example.com", "0800", "Data Wizard", 3, "applied", "LinkedIn"),
        header=SOURCE_HEADER,
    )

    existing.refresh_from_db()
    assert existing.source == "referral"
    assert existing.applications.count() == 1
