# backend/loans/tests/test_climate_services.py
import pytest
from django.test import TestCase
from django.utils import timezone
from asgiref.sync import sync_to_async
from decimal import Decimal
from loans.climate_services import ClimateAdaptiveLoanService
from loans.external.weather_api import WeatherService
from farmers.models import Farmer
from loans.models import Loan, LoanProduct, PaymentSchedule
from authentication.models import User 

class TestClimateAdaptiveLoans(TestCase):
    def setUp(self):
        # First create a user
        self.user = User.objects.create(
            username="test_climate_user",
            email="climate_test@example.com",
            password="password123",
            role="FARMER",
            phone_number="+250789123456"
        )
        
        # Create test farmer with user reference
        self.farmer = Farmer.objects.create(
            user=self.user,  # Add this line
            name="Test Climate Farmer",
            phone_number="+250789123456",
            location="Nyagatare",
            farm_size=2.5
        )

        # Create test loan product - Add this block
        self.loan_product = LoanProduct.objects.create(
            name="Test Climate Product",
            description="Test product for climate adaptive loans",
            min_amount=10000,
            max_amount=50000,
            interest_rate=15,
            duration_days=30,
            is_active=True,
            requirements="{}",
            created_at=timezone.now(),
            grace_period_days=5,
            repayment_schedule_type='FIXED'
        )

    @pytest.mark.asyncio
    async def test_weather_conditions_check(self):
        # Create a weather service to test directly
        weather_service = WeatherService()
        conditions = await weather_service.get_conditions("Nyagatare")
        
        # Check that we got reasonable values back
        self.assertIn('drought_index', conditions)
        self.assertIn('flood_index', conditions)
        self.assertGreaterEqual(conditions['drought_index'], 0)
        self.assertLessEqual(conditions['drought_index'], 1)
        
    @pytest.mark.asyncio
    async def test_payment_extension_due_to_weather(self):
        # Create an active loan
        @sync_to_async
        def create_loan_with_schedule():
            loan = Loan.objects.create(
                farmer=self.farmer,
                loan_product=self.loan_product,
                amount_requested=Decimal("20000"),
                amount_approved=Decimal("20000"),
                status='APPROVED',
                disbursement_status='COMPLETED',
                application_date=timezone.now(),
                disbursement_date=timezone.now(),
                due_date=timezone.now() + timezone.timedelta(days=30)
            )
            
            # Create a payment schedule
            payment_date = timezone.now() + timezone.timedelta(days=15)
            schedule = PaymentSchedule.objects.create(
                loan=loan,
                installment_number=1,
                due_date=payment_date,
                principal_amount=Decimal("10000"),
                interest_amount=Decimal("1500"),
                amount=Decimal("11500"),
                status='PENDING'
            )
            
            return loan, schedule, payment_date
        
        loan, schedule, original_date = await create_loan_with_schedule()
        
        # Set up our weather service to report drought conditions for this test
        # This is a mock, so we'll monkey patch the get_conditions method
        original_get_conditions = WeatherService.get_conditions
        
        async def mock_get_conditions(self, location):
            return {'drought_index': 0.8, 'flood_index': 0.1}
        
        WeatherService.get_conditions = mock_get_conditions
        
        try:
            # Run the climate check service
            climate_service = ClimateAdaptiveLoanService()
            await climate_service.check_for_adverse_conditions()
            
            # Refresh our schedule from the database
            @sync_to_async
            def refresh_schedule():
                return PaymentSchedule.objects.get(id=schedule.id)
            
            updated_schedule = await refresh_schedule()
            
            # Check that the due date was extended by 30 days
            self.assertGreater(updated_schedule.due_date, original_date)
            self.assertEqual((updated_schedule.due_date - original_date).days, 30)
            
        finally:
            # Restore the original method
            WeatherService.get_conditions = original_get_conditions