import os
import dj_database_url
from .settings import *

DEBUG = 'RENDER' not in os.environ
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
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.onrender.com', 'agrifinance-api.onrender.com']

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "https://agrifinance-api.onrender.com",
    "http://localhost:3000",

]
CORS_ALLOW_CREDENTIALS = True


# Check required environment variables
REQUIRED_ENV_VARS = [
    'SECRET_KEY', 
    'AT_USERNAME', 
    'AT_API_KEY',
    'MOMO_SUBSCRIPTION_KEY',
    'MOMO_COLLECTION_KEY',
    'MOMO_API_USER',
    'MOMO_API_KEY',
    'MOMO_API_SECRET',
    'MOMO_ENVIRONMENT',
    'MOMO_API_URL'
]

# Generate a warning for missing environment variables
for var in REQUIRED_ENV_VARS:
    if not os.environ.get(var):
        print(f"Warning: {var} environment variable is not set!")


# Security settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000 
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'