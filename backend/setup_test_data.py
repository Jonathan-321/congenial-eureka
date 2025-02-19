import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()
from asgiref.sync import sync_to_async
import asyncio
from decimal import Decimal
from farmers.models import Farmer
from loans.models import LoanProduct
from authentication.models import User

async def setup_test_data():
    # Create test user and farmer
    user = await sync_to_async(User.objects.create_user)(
        username="testfarmer",
        password="testpass123",
        email="farmer@test.com",
        role="FARMER",
        phone_number="250789123456"
    )
    
    farmer = await sync_to_async(Farmer.objects.create)(
        user=user,
        name="Test Farmer",
        location="Kigali",
        farm_size=2.5,
        phone_number="250789123456"
    )
    
    # Create loan product
    product = await sync_to_async(LoanProduct.objects.create)(
        name="Quick Loan",
        description="Short term agricultural loan",
        min_amount=Decimal("10.00"),
        max_amount=Decimal("1000.00"),
        interest_rate=Decimal("15.00"),
        duration_days=30  # Changed from term_days to duration_days
    )
    
    print(f"Created test farmer: {farmer.name}")
    print(f"Created loan product: {product.name}")
    return farmer, product

if __name__ == "__main__":
    asyncio.run(setup_test_data())