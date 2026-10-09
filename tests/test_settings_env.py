import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured
from storages.backends.s3 import S3Storage

from config.env import env_bool, env_list, resume_storage, secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

S3_ENV = {
    "RESUMES_S3_BUCKET": "talentflow-resumes",
    "RESUMES_S3_ACCESS_KEY_ID": "key-id",
    "RESUMES_S3_SECRET_ACCESS_KEY": "secret",
    "RESUMES_S3_ENDPOINT_URL": "https://account.r2.cloudflarestorage.com",
}


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, False), ("", False), ("True", True), ("1", True), ("false", False), ("no", False)],
)
def test_env_bool_defaults_to_false(value, expected):
    environ = {} if value is None else {"DEBUG": value}

    assert env_bool(environ, "DEBUG") is expected


def test_env_list_splits_and_trims():
    assert env_list({"HOSTS": " a.com, ,b.com "}, "HOSTS") == ["a.com", "b.com"]


def test_secret_key_is_required_without_debug():
    with pytest.raises(ImproperlyConfigured):
        secret_key({}, debug=False)


def test_secret_key_has_a_dev_fallback_only_with_debug():
    assert secret_key({}, debug=True).startswith("django-insecure-")
    assert secret_key({"SECRET_KEY": "real"}, debug=False) == "real"


def test_resumes_use_local_private_folder_by_default(tmp_path):
    config = resume_storage({}, local_location=tmp_path)

    assert config["BACKEND"] == "django.core.files.storage.FileSystemStorage"
    assert config["OPTIONS"]["location"] == tmp_path


def test_resumes_use_a_private_s3_bucket_when_configured(tmp_path):
    config = resume_storage(S3_ENV, local_location=tmp_path)

    assert config["BACKEND"] == "storages.backends.s3.S3Storage"
    storage = S3Storage(**config["OPTIONS"])
    assert storage.bucket_name == "talentflow-resumes"
    assert storage.endpoint_url == S3_ENV["RESUMES_S3_ENDPOINT_URL"]
    assert storage.default_acl is None
    assert storage.file_overwrite is False


def test_incomplete_s3_settings_fail_fast(tmp_path):
    environ = {**S3_ENV, "RESUMES_S3_SECRET_ACCESS_KEY": ""}

    with pytest.raises(ImproperlyConfigured, match="RESUMES_S3_SECRET_ACCESS_KEY"):
        resume_storage(environ, local_location=tmp_path)


def _load_settings(**env):
    """Import the real settings module in a fresh process with the given variables."""
    environ = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings", **env}
    return subprocess.run(
        [sys.executable, "-c", "import django; django.setup(); from django.conf import settings; print(settings.DEBUG)"],
        cwd=BASE_DIR,
        env=environ,
        capture_output=True,
        text=True,
    )


def test_startup_fails_without_secret_key_when_debug_is_off():
    # Empty values override .env (python-dotenv never replaces existing variables).
    result = _load_settings(DEBUG="False", SECRET_KEY="")

    assert result.returncode != 0
    assert "SECRET_KEY must be set when DEBUG is False" in result.stderr


def test_debug_defaults_to_false():
    result = _load_settings(DEBUG="", SECRET_KEY="any-secret-value")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"
