"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Initialize Django
application = get_wsgi_application()

# Create superuser if environment variables are set
if all(k in os.environ for k in ('DJANGO_SUPERUSER_USERNAME', 'DJANGO_SUPERUSER_EMAIL', 'DJANGO_SUPERUSER_PASSWORD')):
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        username = os.environ['DJANGO_SUPERUSER_USERNAME']
        email = os.environ['DJANGO_SUPERUSER_EMAIL']
        password = os.environ['DJANGO_SUPERUSER_PASSWORD']
        
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password)
            print(f"Superuser {username} created successfully")
        else:
            print(f"Superuser {username} already exists")
    except Exception as e:
        print(f"Error creating superuser: {e}")