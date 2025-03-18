import os
import sys
import django
from django.conf import settings
import pytest

# Add the project directory to the sys.path
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_path)

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """Set environment variables for testing"""
    os.environ['DJANGO_TESTING'] = 'True'
    os.environ['TEST_MODE'] = 'True'
    return
