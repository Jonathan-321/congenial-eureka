import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

import asyncio
from decimal import Decimal
from asgiref.sync import sync_to_async
from django.db import transaction
from loans.momo_integration import MoMoAPI
from loans.models import Loan, LoanProduct
from farmers.models import Farmer

async def test_full_loan_flow():
    print("\nTesting Full Loan Flow")
    print("---------------------")
    
    try:
        # Setup async database operations
        get_farmer = sync_to_async(Farmer.objects.get)
        get_product = sync_to_async(LoanProduct.objects.get)
        create_loan = sync_to_async(Loan.objects.create)
        
        # Get test data
        phone = "250789123456"
        print("\n1. Getting test farmer...")
        farmer = await get_farmer(phone_number=phone)
        print(f"Found farmer: {farmer.name}")
        
        print("\n2. Getting loan product...")
        loan_product = await get_product(name="Quick Loan")
        print(f"Found loan product: {loan_product.name}")
        
        # Create loan application
        print("\n3. Creating loan application...")
        loan = await create_loan(
            farmer=farmer,
            loan_product=loan_product,
            amount_requested=Decimal("50.00"),
            amount_approved=Decimal("50.00"),
            status='PENDING'
        )
        print(f"Created loan application: {loan.id}")
        
        # Initialize MoMo API
        momo = MoMoAPI()
        
        # Get access token
        print("\n4. Getting MoMo access token...")
        token = await momo.get_access_token()
        print("✅ Token received")
        
        # Process and disburse loan
        print("\n5. Processing and disbursing loan...")
        result = await momo.initiate_disbursement(
            loan_id=loan.id,
            amount=Decimal("50.00"),
            phone_number=phone
        )
        print(f"Disbursement result: {result}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_full_loan_flow())