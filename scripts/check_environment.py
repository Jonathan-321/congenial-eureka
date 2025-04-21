#!/usr/bin/env python
"""
Environment checker script for climate data services
Verifies all dependencies and environment variables needed for the climate data update commands
"""

import sys
import os
import importlib
import subprocess
from pathlib import Path

# Add the project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Required Python packages
REQUIRED_PACKAGES = [
    "django",
    "celery",
    "python-dotenv",
    "aiohttp",
    "psycopg2",
    "django-environ",
]

# Required environment variables
REQUIRED_ENV_VARS = [
    "OPENWEATHER_API_KEY",
    "SENTINEL_INSTANCE_ID",
    "SENTINEL_API_KEY",
    "SENTINEL_OAUTH_CLIENT_ID", 
    "SENTINEL_OAUTH_CLIENT_SECRET",
]

def check_package(package_name):
    """Check if a Python package is installed"""
    try:
        importlib.import_module(package_name.replace("-", "_"))
        return True
    except ImportError:
        return False

def check_postgres():
    """Check if PostgreSQL is installed and accessible"""
    try:
        result = subprocess.run(
            ["pg_config", "--version"], 
            capture_output=True, 
            text=True,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False

def check_environment_variables():
    """Check if required environment variables are set"""
    missing_vars = []
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            missing_vars.append(var)
    return missing_vars

def main():
    """Run all environment checks"""
    print("Checking environment for climate data services...")
    
    # Check Python packages
    missing_packages = []
    for package in REQUIRED_PACKAGES:
        if not check_package(package):
            missing_packages.append(package)
    
    if missing_packages:
        print("\n❌ Missing Python packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall missing packages with:")
        print(f"  pip install {' '.join(missing_packages)}")
    else:
        print("\n✅ All required Python packages are installed.")
    
    # Check PostgreSQL
    if check_postgres():
        print("\n✅ PostgreSQL is installed and accessible.")
    else:
        print("\n❌ PostgreSQL is not installed or not in PATH.")
        print("  Install PostgreSQL or add it to your PATH.")
    
    # Check environment variables
    missing_vars = check_environment_variables()
    if missing_vars:
        print("\n❌ Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nAdd these variables to your .env file or environment.")
    else:
        print("\n✅ All required environment variables are set.")
    
    # Summary
    if not missing_packages and check_postgres() and not missing_vars:
        print("\n✅ Environment is properly configured for climate data services.")
        return 0
    else:
        print("\n❌ Environment setup is incomplete. Address the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 