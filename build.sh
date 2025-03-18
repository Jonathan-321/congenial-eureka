#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Run Django commands
cd backend
python manage.py collectstatic --no-input
python manage.py migrate
