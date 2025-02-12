from django.conf import settings
import os
from dotenv import load_dotenv

load_dotenv()

def test_settings():
    print("\nTesting Environment Variables:")
    print(f"MOMO_SUBSCRIPTION_KEY: {os.getenv('MOMO_SUBSCRIPTION_KEY')}")
    print(f"MOMO_API_USER: {os.getenv('MOMO_API_USER')}")
    print(f"MOMO_API_KEY: {os.getenv('MOMO_API_KEY')}")
    print(f"MOMO_ENVIRONMENT: {os.getenv('MOMO_ENVIRONMENT')}")
    print(f"MOMO_API_URL: {os.getenv('MOMO_API_URL')}")
    
    print("\nTesting Django Settings:")
    print(f"MOMO_SUBSCRIPTION_KEY: {getattr(settings, 'MOMO_SUBSCRIPTION_KEY', 'Not Found')}")
    print(f"MOMO_API_USER: {getattr(settings, 'MOMO_API_USER', 'Not Found')}")
    print(f"MOMO_API_KEY: {getattr(settings, 'MOMO_API_KEY', 'Not Found')}")
    print(f"MOMO_ENVIRONMENT: {getattr(settings, 'MOMO_ENVIRONMENT', 'Not Found')}")
    print(f"MOMO_API_URL: {getattr(settings, 'MOMO_API_URL', 'Not Found')}")

if __name__ == "__main__":
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

    django.setup()
    test_settings()