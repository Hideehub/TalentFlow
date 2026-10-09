"""Small helpers for reading settings from the environment.

Kept as plain functions (no Django imports at module level besides the exception) so
the rules can be unit-tested without reloading the settings module.
"""

from django.core.exceptions import ImproperlyConfigured

TRUE_VALUES = {"1", "true", "yes", "on"}


def env_bool(environ, name, default=False):
    value = environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in TRUE_VALUES


def env_list(environ, name, default=""):
    return [item.strip() for item in environ.get(name, default).split(",") if item.strip()]


def secret_key(environ, *, debug):
    """The SECRET_KEY, or a fixed dev-only key when DEBUG is on. Fails fast otherwise."""
    key = environ.get("SECRET_KEY", "").strip()
    if key:
        return key
    if debug:
        return "django-insecure-local-development-only"
    raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is False.")


RESUME_S3_REQUIRED = (
    "RESUMES_S3_BUCKET",
    "RESUMES_S3_ACCESS_KEY_ID",
    "RESUMES_S3_SECRET_ACCESS_KEY",
)


def resume_storage(environ, *, local_location):
    """STORAGES["resumes"]: S3/R2 when its variables are set, else a local private folder.

    The bucket stays private: no ACL is sent (objects inherit the bucket's private
    policy) and files are only ever streamed through the app's scoped download view.
    """
    if not environ.get("RESUMES_S3_BUCKET"):
        return {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": local_location},
        }

    missing = [name for name in RESUME_S3_REQUIRED if not environ.get(name)]
    if missing:
        raise ImproperlyConfigured(f"Resume storage is missing: {', '.join(missing)}")

    return {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": environ["RESUMES_S3_BUCKET"],
            "access_key": environ["RESUMES_S3_ACCESS_KEY_ID"],
            "secret_key": environ["RESUMES_S3_SECRET_ACCESS_KEY"],
            "endpoint_url": environ.get("RESUMES_S3_ENDPOINT_URL") or None,
            "region_name": environ.get("RESUMES_S3_REGION") or "auto",
            "signature_version": "s3v4",
            "default_acl": None,
            "querystring_auth": True,
            "file_overwrite": False,
        },
    }
