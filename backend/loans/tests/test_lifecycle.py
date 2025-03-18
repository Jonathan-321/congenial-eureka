from datetime import timedelta
import os
from django.test import TestCase
import pytest
from decimal import Decimal
from django.utils import timezone
from authentication.models import User
from farmers.models import Farmer
from loans.models import Loan, LoanProduct, PaymentSchedule, LoanRepayment
from loans.lifecycle_service import LoanLifecycleService
from loans.repayment_service import RepaymentService
from asgiref.sync import sync_to_async
from unittest.mock import patch, AsyncMock

class TestLoanLifecycle(TestCase):
    def setUp(self):
        # Set testing environment variable
        os.environ['DJANGO_TESTING'] = 'True'
        
        # Create a test user
        self.user = User.objects.create(
            username="lifecycle_test_user",
            email="lifecycle@example.com",
            password="password123",
            role="FARMER",
            phone_number="+250789123456"
        )
        
        # Create test farmer
        self.farmer = Farmer.objects.create(
            user=self.user,
            name="Lifecycle Test Farmer",
            phone_number="+250789123456",
            location="Kigali",
            farm_size=2.5
        )
        
        # Create a test loan product
        self.loan_product = LoanProduct.objects.create(
            name="Lifecycle Test Product",
            description="For testing loan lifecycle",
            min_amount=Decimal("100.00"),
            max_amount=Decimal("1000.00"),
            interest_rate=Decimal("5.00"),
            duration_days=30,
            repayment_schedule_type="FIXED"
        )
        
        # Create a test loan
        self.loan = Loan.objects.create(
            farmer=self.farmer,
            loan_product=self.loan_product,
            amount_requested=Decimal("500.00"),
            status='PENDING',
            credit_score=75
        )
        
        self.lifecycle_service = LoanLifecycleService()
        self.repayment_service = RepaymentService()
        
        # Mock SMS service
        self.sms_patcher = patch('loans.sms_service.SMSService.send_sms', new_callable=AsyncMock)
        self.mock_sms = self.sms_patcher.start()
        self.mock_sms.return_value = (True, {"SMSMessageData": {"Message": "Sent"}})

    def tearDown(self):
        self.sms_patcher.stop()
        # Clear testing environment variable 
        os.environ.pop("DJANGO_TESTING", None)

    @pytest.mark.asyncio
    async def test_full_loan_lifecycle(self):
        print("\nStarting loan lifecycle test")

        # Test loan approval
        print("Testing loan approval...")
        success, loan = await self.lifecycle_service.approve_loan(self.loan.id)
        self.assertTrue(success, f"Loan approval failed: {loan if not success else ''}")
        
        # Verify loan status after approval
        @sync_to_async
        def verify_loan_status():
            loan = Loan.objects.get(id=self.loan.id)
            print(f"DEBUG - Loan status after approval: {loan.status}")
            return loan.status
        
        loan_status = await verify_loan_status()
        self.assertEqual(loan_status, 'APPROVED', "Loan should be in APPROVED status after approval")
        
        # Test loan disbursement
        @sync_to_async
        def disburse_loan():
            loan = Loan.objects.get(id=self.loan.id)
            loan.status = 'DISBURSED'
            loan.disbursement_date = timezone.now()
            loan.amount_approved = Decimal('500.00')
            loan.save()
            return loan
        
        loan = await disburse_loan()
        
        # Create payment schedules
        @sync_to_async
        def create_payment_schedules():
            PaymentSchedule.objects.create(
                loan=loan,
                installment_number=1,
                due_date=timezone.now() + timedelta(days=30),
                principal_amount=Decimal('500.00'),
                interest_amount=Decimal('25.00'),
                amount=Decimal('525.00'),
                status='PENDING',
                amount_paid=Decimal('0.00'),
                penalty_amount=Decimal('0.00')
            )
        
        await create_payment_schedules()
        
        # Verify loan is ready for payment
        loan_status = await verify_loan_status()
        self.assertEqual(loan_status, 'DISBURSED', "Loan should be in DISBURSED status before payment")
        
        # Test payment processing
        payment_data = {
            'reference': str(loan.id),
            'amount': '525.00',
            'phone_number': self.farmer.phone_number
        }
        
        print("Processing payment...")
        success, message = await self.repayment_service.process_payment(payment_data)
        self.assertTrue(success, f"Payment processing failed: {message}")
        
        # Verify payment was recorded
        @sync_to_async
        def verify_payment():
            loan = Loan.objects.get(id=self.loan.id)
            repayment = loan.repayments.first()  # Using the related_name we fixed earlier
            return loan, repayment
        
        loan, repayment = await verify_payment()
        self.assertIsNotNone(repayment, "Repayment should be recorded")
        self.assertEqual(repayment.amount, Decimal('525.00'), "Repayment amount should match")
        
        # Test loan completion
        print("Completing loan process...")
        success, message = await self.lifecycle_service.complete_loan_process(loan.id)
        self.assertTrue(success, f"Loan completion failed: {message}")
        
        # Final status check
        @sync_to_async
        def final_status_check():
            return Loan.objects.get(id=self.loan.id).status
        
        final_status = await final_status_check()
        self.assertEqual(final_status, 'PAID', "Loan should be marked as PAID after completion")
        
        # Verify SMS notifications
        self.assertTrue(self.mock_sms.called, "SMS notifications should have been sent")