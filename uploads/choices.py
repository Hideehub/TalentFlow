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
    "source": (
        "source",
        "candidate source",
        "channel",
    ),
}

OPTIONAL_CANDIDATE_FIELDS = ("source",)
REQUIRED_CANDIDATE_FIELDS = tuple(
    field for field in CANDIDATE_HEADER_ALIASES if field not in OPTIONAL_CANDIDATE_FIELDS
)

MAX_IMPORT_ROWS = 1000
MAX_UPLOAD_SIZE = 2 * 1024 * 1024
