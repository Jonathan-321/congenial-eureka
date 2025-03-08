import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

import asyncio
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
import random
from asgiref.sync import sync_to_async
from loans.models import Loan, PaymentSchedule
from loans.services import PaymentScheduleService, LoanService
from farmers.models import Farmer
from loans.models import LoanProduct
from authentication.models import User

async def test_payment_schedule():
    print("\nTesting Payment Schedule Management")
    print("----------------------------------")
    
    try:
        # Generate random phone numbers to avoid conflicts
        random_suffix = random.randint(10000, 99999)
        user_phone = f"+25078{random_suffix}"
        farmer_phone = f"+25079{random_suffix}"
        
        print(f"Using test phone numbers: User: {user_phone}, Farmer: {farmer_phone}")
        
        # Create a test user first
        user = await User.objects.acreate(
            username=f"test_farmer_{random_suffix}",
            email=f"test{random_suffix}@example.com",
            password="password123",
            role="FARMER",
            phone_number=user_phone
        )
        
        # Setup test data
        farmer = await Farmer.objects.acreate(
            user=user,
            name="Schedule Test Farmer",
            phone_number=farmer_phone,
            location="Kigali",
            farm_size=2.5
        )
        
        # Use duration_days instead of term_months
        product = await LoanProduct.objects.acreate(
            name=f"Term Loan {random_suffix}",
            min_amount=Decimal("100.00"),
            max_amount=Decimal("1000.00"),
            interest_rate=Decimal("15.00"),
            duration_days=90  # 3 months = 90 days
        )
        
        loan = await Loan.objects.acreate(
            farmer=farmer,
            loan_product=product,
            amount_requested=Decimal("300.00"),
            amount_approved=Decimal("300.00"),
            application_date=timezone.now(),
            disbursement_date=timezone.now(),
            status='APPROVED'
        )
        
        # Create payment schedule
        loan_service = LoanService()
        await loan_service.create_payment_schedule(loan)
        
        # Verify schedules were created
        # FIX: Wrap the queryset in sync_to_async
        @sync_to_async
        def get_schedules():
            return list(PaymentSchedule.objects.filter(loan=loan))
            
        schedules = await get_schedules()
        print(f"\n1. Created {len(schedules)} payment schedules:")
        
        for i, schedule in enumerate(schedules):
            print(f"  Schedule {i+1}: Amount {schedule.amount}, Due {schedule.due_date.strftime('%Y-%m-%d')}")
        
        # Test partial payment
        print("\n2. Testing partial payment...")
        payment_service = PaymentScheduleService()
        result = await payment_service.apply_payment(loan, Decimal("50.00"))
        
        print(f"  Payment allocation: {result}")
        
        # Check updated schedule status
        # FIX: Wrap the queryset in sync_to_async
        @sync_to_async
        def get_updated_schedules():
            return list(PaymentSchedule.objects.filter(loan=loan))
            
        updated_schedules = await get_updated_schedules()
        for i, schedule in enumerate(updated_schedules):
            print(f"  Schedule {i+1}: Status {schedule.status}, Amount paid {schedule.amount_paid}")
        
        # Test overdue detection
        print("\n3. Testing overdue detection...")
        # Make the first schedule overdue
        first_schedule = await PaymentSchedule.objects.filter(loan=loan).afirst()
        first_schedule.due_date = timezone.now() - timedelta(days=5)
        await first_schedule.asave()
        
        # Check overdue
        await payment_service.check_overdue_payments()
        
        # Verify overdue status
        updated_schedule = await PaymentSchedule.objects.aget(id=first_schedule.id)
        print(f"  Schedule status: {updated_schedule.status}")
        print(f"  Penalty amount: {updated_schedule.penalty_amount}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

# Run the test
if __name__ == "__main__":
    asyncio.run(test_payment_schedule())