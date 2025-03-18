#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Set Django settings module explicitly
export DJANGO_SETTINGS_MODULE=backend.production

# Run Django commands
cd backend
python manage.py collectstatic --no-input
python manage.py migrate
