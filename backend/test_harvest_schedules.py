# Create a new file: backend/test_harvest_schedules.py

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

import asyncio
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta, datetime
import random
from asgiref.sync import sync_to_async
from loans.models import Loan, PaymentSchedule, CropCycle, LoanProduct
from loans.services import LoanService, PaymentScheduleService
from farmers.models import Farmer
from authentication.models import User

async def test_harvest_schedule():
    print("\nTesting Harvest-Based Payment Schedule")
    print("-------------------------------------")
    
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
            name="Harvest Test Farmer",
            phone_number=farmer_phone,
            location="Kigali",
            farm_size=2.5
        )
        
        # Create a harvest-based loan product
        product = await LoanProduct.objects.acreate(
            name=f"Harvest Loan {random_suffix}",
            min_amount=Decimal("100.00"),
            max_amount=Decimal("1000.00"),
            interest_rate=Decimal("15.00"),
            duration_days=180,  # 6 months
            repayment_schedule_type='HARVEST',
            grace_period_days=30  # 30 days after harvest
        )
        
        # Create loan
        loan = await Loan.objects.acreate(
            farmer=farmer,
            loan_product=product,
            amount_requested=Decimal("600.00"),
            amount_approved=Decimal("600.00"),
            application_date=timezone.now(),
            disbursement_date=timezone.now(),
            status='APPROVED'
        )
        
        # Create crop cycles
        today = timezone.now().date()
        
        # Create two harvest dates - one in 2 months, one in 4 months
        harvest_dates = [
            today + timedelta(days=60),  # 2 months from now
            today + timedelta(days=120)  # 4 months from now
        ]
        
        for i, harvest_date in enumerate(harvest_dates):
            planting_date = harvest_date - timedelta(days=45)  # 45 days before harvest
            await CropCycle.objects.acreate(
                farmer=farmer,
                crop_type='MAIZE' if i == 0 else 'BEANS',
                planting_date=planting_date,
                expected_harvest_date=harvest_date,
                notes=f"Test crop cycle {i+1}"
            )
        
        # Create harvest-based payment schedule
        loan_service = LoanService()
        await loan_service.create_harvest_based_schedule(loan, harvest_dates)
        
        # Verify schedules were created
        @sync_to_async
        def get_schedules():
            return list(PaymentSchedule.objects.filter(loan=loan))
            
        schedules = await get_schedules()
        print(f"\n1. Created {len(schedules)} harvest-based payment schedules:")
        
        for i, schedule in enumerate(schedules):
            print(f"  Schedule {i+1}: Amount {schedule.amount}, Due {schedule.due_date.strftime('%Y-%m-%d')}")
            # Verify due dates match harvest dates + grace period
            expected_due_date = harvest_dates[i] + timedelta(days=product.grace_period_days)
            print(f"  Expected due date: {expected_due_date.strftime('%Y-%m-%d')}")
            assert schedule.due_date.date() == expected_due_date, "Due date doesn't match expected date"
        
        print("\nAll tests passed successfully!")
        
    except Exception as e:
        print(f"Error during test: {str(e)}")
    
if __name__ == "__main__":
    asyncio.run(test_harvest_schedule())