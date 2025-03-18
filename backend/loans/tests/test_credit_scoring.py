# backend/loans/tests/test_credit_scoring.py

import pytest
from django.test import TestCase
from django.utils import timezone
from asgiref.sync import sync_to_async
from decimal import Decimal
from loans.services import DynamicCreditScoringService
from farmers.models import Farmer
from loans.models import Loan, LoanProduct
from authentication.models import User 

class TestDynamicCreditScoring(TestCase):
    def setUp(self):
        # First create a user
        self.user = User.objects.create(
            username="test_credit_user",
            email="credit_test@example.com",
            password="password123",
            role="FARMER",
            phone_number="+250789123456"
        )
        
        # Create test farmer with user reference
        self.farmer = Farmer.objects.create(
            user=self.user,  
            name="Test Credit Farmer",
            phone_number="+250789123456",
            location="Kigali",
            farm_size=2.5
        )

         # Create a loan product 
        self.loan_product = LoanProduct.objects.create(
            name="Test Credit Product",
            description="Test product for credit scoring",
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
    async def test_dynamic_credit_scoring(self):
        # Create a completed loan to influence credit score
        @sync_to_async
        def create_completed_loan():
            loan = Loan.objects.create(
                farmer=self.farmer,
                loan_product=self.loan_product,
                amount_requested=Decimal("20000"),
                amount_approved=Decimal("20000"),
                status='PAID',
                application_date=timezone.now() - timezone.timedelta(days=100),
                disbursement_date=timezone.now() - timezone.timedelta(days=90),
                due_date=timezone.now() - timezone.timedelta(days=30)
            )
            return loan
        
        await create_completed_loan()
        
        # Generate dynamic credit score
        scoring_service = DynamicCreditScoringService()
        score = await scoring_service.generate_credit_score(self.farmer)
        
        # Basic validation - score should be in range
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        
        # Since we added a successfully repaid loan, score should be reasonably good
        self.assertGreaterEqual(score, 50)