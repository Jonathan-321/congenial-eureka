# backend/loans/tests/test_tokenization.py

import pytest
from django.test import TestCase
from django.utils import timezone
from asgiref.sync import sync_to_async
from decimal import Decimal
from loans.tokenization_service import TokenizedLoanService
from farmers.models import Farmer
from loans.models import Loan, LoanProduct, ApprovedVendor, LoanToken
from authentication.models import User 

class TestTokenizedLoans(TestCase):
    def setUp(self):
        # Create test farmer
        self.user = User.objects.create(
            username="test_token_user",
            email="token_test@example.com",
            password="password123",
            role="FARMER",
            phone_number="+250789123456"
        )
        
        # Now create test farmer with user reference
        self.farmer = Farmer.objects.create(
            user=self.user,  # Add this line
            name="Test Token Farmer",
            phone_number="+250789123456",
            location="Kigali",
            farm_size=2.5
        )
        
        # Create test loan product - Add this block
        self.loan_product = LoanProduct.objects.create(
            name="Test Token Product",
            description="Test product for tokenization",
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
        # Create an approved vendor
        self.vendor = ApprovedVendor.objects.create(
            name="Test Agro Supply Shop",
            phone_number="+250789654321",
            location="Kigali",
            business_type="GENERAL"
        )

    @pytest.mark.asyncio
    async def test_token_disbursement(self):
        # Create a loan
        @sync_to_async
        def create_loan():
            return Loan.objects.create(
                farmer=self.farmer,
                loan_product=self.loan_product,
                amount_requested=Decimal("20000"),
                amount_approved=Decimal("20000"),
                status='APPROVED',
                application_date=timezone.now(),
                disbursement_date=timezone.now()
            )
        
        loan = await create_loan()
        
        # Disburse as token
        token_service = TokenizedLoanService()
        success, result = await token_service.disburse_tokenized_loan(loan)
        
        # Check for successful token creation
        self.assertTrue(success)
        self.assertIsInstance(result, LoanToken)
        
        # Verify token details
        self.assertEqual(result.loan, loan)
        self.assertEqual(result.amount, loan.amount_approved)
        self.assertEqual(result.status, 'ACTIVE')
        
        # Verify loan status was updated
        @sync_to_async
        def get_updated_loan():
            return Loan.objects.get(id=loan.id)
        
        updated_loan = await get_updated_loan()
        self.assertEqual(updated_loan.disbursement_status, 'COMPLETED')
        self.assertEqual(updated_loan.momo_reference, result.token)