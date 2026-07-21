import re
from collections import Counter
from zipfile import BadZipFile

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models.functions import Lower
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from accounts.tenancy import get_user_company
from recruitment.choices import CANDIDATE_STATUS
from recruitment.models import Candidate, JobOpening

from .choices import (
    CANDIDATE_HEADER_ALIASES,
    MAX_IMPORT_ROWS,
    REQUIRED_CANDIDATE_FIELDS,
)


class CandidateImportError(Exception):
    pass


def _normalize_header(value):
    text = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def _header_map(header_row):
    normalized_aliases = {
        _normalize_header(alias): field
        for field, aliases in CANDIDATE_HEADER_ALIASES.items()
        for alias in aliases
    }

    return {
        normalized_aliases[_normalize_header(value)]: index
        for index, value in enumerate(header_row)
        if _normalize_header(value) in normalized_aliases
    }


def _select_worksheet(workbook):
    for worksheet in workbook.worksheets:
        header_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
        mapping = _header_map(header_row)
        if all(field in mapping for field in REQUIRED_CANDIDATE_FIELDS):
            return worksheet, mapping

    raise CandidateImportError("No sheet contains all required candidate columns.")


def _cell_value(row, mapping, field):
    index = mapping[field]
    return row[index] if index < len(row) else None


def _normalize_name(value):
    name = str(value or "").strip()
    return name.title() if name.isupper() or name.islower() else name


def _normalize_status(value):
    return str(value or "").strip().lower().replace(" ", "_")


def _normalize_experience(value):
    if value in (None, ""):
        return None

    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None

    return number if number >= 0 else None


def candidate_import_preview(uploaded_file, *, user=None):
    try:
        workbook = load_workbook(uploaded_file, read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, OSError, ValueError) as exc:
        raise CandidateImportError("The uploaded Excel file could not be read.") from exc

    worksheet, mapping = _select_worksheet(workbook)
    raw_rows = list(
        worksheet.iter_rows(
            min_row=2,
            max_row=MAX_IMPORT_ROWS + 2,
            values_only=True,
        )
    )
    non_empty_rows = [row for row in raw_rows if any(value not in (None, "") for value in row)]
    workbook.close()

    if len(non_empty_rows) > MAX_IMPORT_ROWS:
        raise CandidateImportError(f"Imports are limited to {MAX_IMPORT_ROWS} rows at a time.")

    parsed_rows = []
    for row_number, row in enumerate(non_empty_rows, start=2):
        email = str(_cell_value(row, mapping, "email") or "").strip().lower()
        parsed_rows.append(
            {
                "row_number": row_number,
                "full_name": _normalize_name(_cell_value(row, mapping, "full_name")),
                "email": email,
                "phone": str(_cell_value(row, mapping, "phone") or "").strip(),
                "position_applied_for": str(
                    _cell_value(row, mapping, "position_applied_for") or ""
                ).strip(),
                "years_of_experience": _normalize_experience(
                    _cell_value(row, mapping, "years_of_experience")
                ),
                "status": _normalize_status(_cell_value(row, mapping, "status")),
                "errors": [],
            }
        )

    email_counts = Counter(row["email"] for row in parsed_rows if row["email"])
    company = get_user_company(user)
    existing_candidates = Candidate.objects.annotate(email_key=Lower("email"))
    if company:
        existing_candidates = existing_candidates.filter(company=company)

    existing_emails = {
        email
        for email in existing_candidates
        .filter(email_key__in=[row["email"] for row in parsed_rows if row["email"]])
        .values_list("email_key", flat=True)
    }
    valid_statuses = {value for value, _label in CANDIDATE_STATUS}

    for row in parsed_rows:
        if not row["full_name"]:
            row["errors"].append("Full name is required.")

        if not row["email"]:
            row["errors"].append("Email is required.")
        else:
            try:
                validate_email(row["email"])
            except ValidationError:
                row["errors"].append("Email is invalid.")

            if email_counts[row["email"]] > 1:
                row["errors"].append("Duplicate email in this file.")
            if row["email"] in existing_emails:
                row["errors"].append("A candidate with this email already exists.")

        if not row["phone"]:
            row["errors"].append("Phone number is required.")
        if not row["position_applied_for"]:
            row["errors"].append("Position is required.")
        if row["years_of_experience"] is None:
            row["errors"].append("Experience must be zero or a positive number.")
        if row["status"] not in valid_statuses:
            row["errors"].append("Status is not recognized.")

        row["is_valid"] = not row["errors"]

    return {
        "filename": uploaded_file.name,
        "sheet_name": worksheet.title,
        "rows": parsed_rows,
        "total_rows": len(parsed_rows),
        "valid_rows": sum(row["is_valid"] for row in parsed_rows),
        "invalid_rows": sum(not row["is_valid"] for row in parsed_rows),
    }


def candidate_import_confirm(rows, *, user=None, assigned_recruiter=None):
    valid_rows = [row for row in rows if row.get("is_valid")]
    emails = [row["email"] for row in valid_rows]
    company = get_user_company(user)
    existing_candidates = Candidate.objects.annotate(email_key=Lower("email"))
    if company:
        existing_candidates = existing_candidates.filter(company=company)
    existing_emails = {
        email
        for email in existing_candidates
        .filter(email_key__in=emails)
        .values_list("email_key", flat=True)
    }
    jobs_by_title = {
        job.title.lower(): job
        for job in JobOpening.objects.filter(status="open", company=company)
    }

    candidates = []
    skipped = 0
    for row in valid_rows:
        if row["email"] in existing_emails:
            skipped += 1
            continue

        position = row["position_applied_for"]
        candidates.append(
            Candidate(
                full_name=row["full_name"],
                company=company,
                email=row["email"],
                phone=row["phone"],
                position_applied_for=position,
                job=jobs_by_title.get(position.lower()),
                assigned_recruiter=assigned_recruiter,
                years_of_experience=row["years_of_experience"],
                status=row["status"],
            )
        )

    with transaction.atomic():
        Candidate.objects.bulk_create(candidates)

    return {
        "imported": len(candidates),
        "skipped": skipped,
    }
