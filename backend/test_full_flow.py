import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

import asyncio
from decimal import Decimal
from asgiref.sync import sync_to_async
from loans.momo_integration import MoMoAPI
from loans.models import Loan,LoanRepayment
from loans.services import LoanService

async def test_full_flow():
    print("\nTesting Full Loan Flow (Disbursement + Repayment)")
    print("------------------------------------------------")
    
    try:
        # Get the most recent pending loan
        get_latest_loan = sync_to_async(
            lambda: Loan.objects.filter(
                status='PENDING'
            ).order_by('-application_date').first()
        )
        loan = await get_latest_loan()
        
        if not loan:
            print("No pending loans found")
            return
            
        print(f"\n1. Found most recent loan:")
        print(f"ID: {loan.id}")
        print(f"Amount: {loan.amount_approved} EUR")
        print(f"Status: {loan.status}")
        print(f"Application Date: {loan.application_date}")
        
        # Initialize MoMo API
        momo = MoMoAPI()
        
        # Test repayment
        print("\n2. Testing repayment...")
        repayment_amount = Decimal("5.00")
        print(f"Repayment amount: {repayment_amount} EUR")
        
        # First get collection token
        print("\n3. Getting collection token...")
        token = await momo.get_access_token(is_collection=True)
        print("✅ Collection token received")
        
        # Request payment
        print("\n4. Requesting payment...")
        get_phone = sync_to_async(lambda x: x.farmer.phone_number)
        phone_number = await get_phone(loan)
        
        result = await momo.request_payment(
            loan_id=loan.id,
            amount=repayment_amount,
            phone_number=phone_number
        )
        print(f"Payment request result: {result}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_full_flow())