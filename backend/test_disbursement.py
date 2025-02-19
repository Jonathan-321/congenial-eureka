import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

import asyncio
import uuid
from decimal import Decimal
from django.utils import timezone
from asgiref.sync import sync_to_async
from loans.momo_integration import MoMoAPI
from loans.models import Loan, LoanProduct, Transaction
from farmers.models import Farmer

async def test_disbursement():
    print("\nTesting MTN MoMo Disbursement")
    print("-----------------------------")
    
    momo = MoMoAPI()
    
    try:
        # First get the token
        print("\n1. Getting access token...")
        token = await momo.get_access_token()
        print(f"✅ Token received: {token[:20]}...")
        
        # Setup test data
        phone = "250789123456"  # Test phone number
        amount = Decimal("10.00")
        
        print(f"\n2. Setting up test data...")
        print(f"Phone: {phone}")
        print(f"Amount: {amount} EUR")
        
        # Setup async database operations
        get_farmer = sync_to_async(Farmer.objects.get)
        get_loan_product = sync_to_async(LoanProduct.objects.get)
        create_loan = sync_to_async(Loan.objects.create)
        
        # Get or create test data
        farmer = await get_farmer(phone_number=phone)
        loan_product = await get_loan_product(id=1)
        
        # Create loan
        loan = await create_loan(
            farmer=farmer,
            loan_product=loan_product,
            amount_requested=amount,
            amount_approved=amount,
            status='APPROVED',
            disbursement_status='PENDING'
        )
        
        # Initiate disbursement
        print("\n3. Initiating disbursement...")
        result = await momo.initiate_disbursement(
            loan_id=loan.id,  # Changed to pass loan_id
            amount=amount,
            phone_number=phone
        )
        print(f"Disbursement initiated: {result}")
        
        # Check disbursement status
        if result.get('status') == 'pending':
            print("\n4. Checking disbursement status...")
            await asyncio.sleep(5)
            status = await momo.check_disbursement_status(reference=result['reference'])  # Use reference from result
            print(f"Status: {status}")
        
    except Exception as e:
        print(f"\n❌ Error occurred:")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        
        if hasattr(e, 'response'):
            print("\nResponse Details:")
            print(f"Status Code: {e.response.status_code}")
            print(f"Headers: {e.response.headers}")
            print(f"Body: {e.response.text}")
            
        # Print full exception for debugging
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_disbursement())