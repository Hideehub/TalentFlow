CANDIDATE_HEADER_ALIASES = {
    "full_name": (
        "full_name",
        "full name",
        "applicant name",
        "candidate name",
        "name",
    ),
    "email": (
        "email",
        "e-mail",
        "email address",
    ),
    "phone": (
        "phone",
        "phone number",
        "mobile",
        "mobile number",
    ),
    "position": (
        "position_applied_for",
        "position applied for",
        "role applied",
        "role",
        "position",
    ),
    "years_of_experience": (
        "years_of_experience",
        "years of experience",
        "exp(yrs)",
        "experience",
        "experience years",
    ),
    "status": (
        "status",
        "current stage",
        "stage",
    ),
}

REQUIRED_CANDIDATE_FIELDS = tuple(CANDIDATE_HEADER_ALIASES)

MAX_IMPORT_ROWS = 1000
MAX_UPLOAD_SIZE = 2 * 1024 * 1024
