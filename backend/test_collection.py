import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

import asyncio
import uuid
from decimal import Decimal
from django.utils import timezone
from django.db import models
from asgiref.sync import sync_to_async
from loans.momo_integration import MoMoAPI
from loans.models import Loan, LoanProduct, Transaction
from farmers.models import Farmer


async def test_collection():
    print("\nTesting MTN MoMo Collection/Repayment")
    print("--------------------------")
    
    try:
        # Create database operation functions
        get_or_create_farmer = sync_to_async(Farmer.objects.get_or_create)
        get_or_create_product = sync_to_async(LoanProduct.objects.get_or_create)
        create_loan = sync_to_async(Loan.objects.create)
        get_transaction = sync_to_async(Transaction.objects.get)
        get_loan = sync_to_async(Loan.objects.get)
        
        # Initialize MoMo API first
        momo = MoMoAPI()
        
        # 1. Get access token
        print("\n1. Getting access token...")
        token = await momo.get_access_token(is_collection=True)
        print(f"✅ Token received: {token[:20]}...")
        
        # 2. Create test data
        print("\n2. Creating test data...")
        
        # Create or get test farmer
        farmer, created = await get_or_create_farmer(
            phone_number="250789123456",
            defaults={
                'name': "Test Farmer",
                'location': 'Test Location',
                'farm_size': 5.0
            }
        )
        print(f"{'Created' if created else 'Retrieved'} farmer: {farmer.name}")
        
        # Create or get test loan product
        loan_product, created = await get_or_create_product(
            name="Test Product",
            defaults={
                'description': 'Test loan product',
                'min_amount': Decimal('100.00'),
                'max_amount': Decimal('1000.00'),
                'interest_rate': Decimal('10.00'),
                'term_days': 30
            }
        )
        print(f"{'Created' if created else 'Retrieved'} loan product: {loan_product.name}")
        
        # Create test loan
        loan = await create_loan(
            farmer=farmer,
            loan_product=loan_product,
            amount_requested=Decimal('500.00'),
            amount_approved=Decimal('500.00'),
            status='ACTIVE',
            disbursement_status='COMPLETED',
            disbursement_date=timezone.now()
        )
        print(f"Created test loan with ID: {loan.id}")
        
        # 3. Request payment
        print("\n3. Requesting payment...")
        amount = Decimal("5.00")  # Changed to Decimal
        print(f"Phone: {farmer.phone_number}")
        print(f"Amount: {amount} EUR")
        
        result = await momo.request_payment(
            loan_id=loan.id,
            amount=amount,
            phone_number=farmer.phone_number
        )
        print(f"Payment requested: {result}")
        
        # 4. Check payment status
        if result.get('status') == 'pending':
            print("\n4. Checking payment status...")
            await asyncio.sleep(5)  # Wait 5 seconds before checking
            status = await momo.check_payment_status(reference=result['reference'])  # Added reference=
            print(f"Payment status: {status}")
            
            # Get updated transaction
            transaction = await get_transaction(reference=result['reference'])
            print(f"\nTransaction status: {transaction.status}")
            
            # Get updated loan status
            loan = await get_loan(id=loan.id)
            get_total = sync_to_async(loan.repayments.aggregate)
            total_repaid = await get_total(models.Sum('amount'))
            total_repaid_amount = total_repaid['amount__sum'] or 0
            print(f"Total repaid: {total_repaid_amount} EUR")
            print(f"Loan status: {loan.status}")
        
    except Exception as e:
        print(f"\n❌ Error occurred:")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        
        if hasattr(e, 'response'):
            print("\nResponse Details:")
            print(f"Status Code: {e.response.status_code}")
            print(f"Headers: {e.response.headers}")
            print(f"Body: {e.response.text}")
            
        # Added full traceback
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_collection())