#!/usr/bin/env bash
# Render build step: install, collect static files, migrate, create role groups.
set -o errexit
set -o pipefail

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py setup_roles

# The demo company is created (or topped up) on every deploy when DEMO_MODE is on.
# seed_demo is safe to rerun.
if [[ "${DEMO_MODE:-False}" =~ ^([Tt]rue|1|yes|on)$ ]]; then
  python manage.py seed_demo
fi
