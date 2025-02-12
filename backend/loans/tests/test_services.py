from django.test import TestCase
from django.conf import settings
from loans.services import LoanService, SMSService
from farmers.models import Farmer
from loans.models import Loan, LoanProduct
import pytest

class TestLoanServices(TestCase):
    def setUp(self):
        # Create test farmer
        self.farmer = Farmer.objects.create(
            name="Test Farmer",
            phone_number="+250789123456",  # Use a sandbox number
            location="Kigali",
            farm_size=2.5
        )
        
        # Create test loan product
        self.loan_product = LoanProduct.objects.create(
            name="Test Product",
            min_amount=10000,
            max_amount=50000,
            interest_rate=15,
            term_days=30
        )

    @pytest.mark.asyncio
    async def test_loan_application_flow(self):
        # Test loan application
        success, result = await LoanService.process_loan_application(
            self.farmer,
            self.loan_product,
            20000
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(result)
        
        # Verify SMS was sent (in sandbox mode)
        # This will work because we're using Africa's Talking sandbox

    def test_credit_scoring(self):
        score = LoanService.calculate_credit_score(self.farmer)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)