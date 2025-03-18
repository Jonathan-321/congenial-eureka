import os
import dj_database_url
from .settings import *

DEBUG = 'RENDER' in os.environ

# Configure DATABASE_URL from Render
if 'DATABASE_URL' in os.environ:
    DATABASES['default'] = dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
    )

# Configure static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Add whitenoise middleware
if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Allowed hosts
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.onrender.com']

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "https://yourappdomain.onrender.com",
    "http://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True

# Security settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
