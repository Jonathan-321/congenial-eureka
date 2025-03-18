#!/usr/bin/env bash
# exit on error
set -o errexit

cd backend
export DJANGO_SETTINGS_MODULE=backend.production
exec gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT