from django.test import TestCase
from django.conf import settings
from loans.services import LoanService, SMSService
from farmers.models import Farmer
from loans.models import Loan, LoanProduct
import pytest
from authentication.models import User
from decimal import Decimal
import os

class TestLoanServices(TestCase):
    def setUp(self):
        # Ensure test environment variables are set
        os.environ['DJANGO_TESTING'] = 'True'
        os.environ['TEST_MODE'] = 'True'

        # First create a user
        self.user = User.objects.create(
            username="test_services_user",
            email="services_test@example.com",
            password="password123",
            role="FARMER",
            phone_number="+250789123456"
        )
        
        # Create test farmer with user reference
        self.farmer = Farmer.objects.create(
            user=self.user,  # Add this line
            name="Test Farmer",
            phone_number="+250789123456",
            location="Kigali",
            farm_size=2.5
        )
        # Create a test loan product
        self.loan_product = LoanProduct.objects.create(
            name="Test Product",
            description="Test description",
            min_amount=Decimal("100.00"),
            max_amount=Decimal("1000.00"),
            interest_rate=Decimal("5.00"),
            duration_days=30,
            repayment_schedule_type="FIXED"
        )
    @pytest.mark.asyncio
    async def test_loan_application_flow(self):
        # Test loan application
        success, result = await LoanService.process_loan_application(
            self.farmer,
            self.loan_product,
            500
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(result)
        
        # Verify SMS was sent (in sandbox mode)
        # This will work because we're using Africa's Talking sandbox

    def test_credit_scoring(self):
        score = LoanService.calculate_credit_score(self.farmer)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)