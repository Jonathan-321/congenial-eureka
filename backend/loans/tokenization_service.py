# backend/loans/tokenization_service.py

import uuid
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from .models import Loan, LoanToken, ApprovedVendor, TokenTransaction
from .momo_integration import MoMoAPI
from .services import SMSService

class TokenizedLoanService:
    def __init__(self):
        self.momo_api = MoMoAPI()
        self.sms_service = SMSService()
    
    async def disburse_tokenized_loan(self, loan):
        """Disburse a loan as tokens that can only be used with approved vendors"""
        # Generate unique token for this loan
        token = str(uuid.uuid4())
        
        # Store token information
        @sync_to_async
        def create_token():
            return LoanToken.objects.create(
                loan=loan,
                token=token,
                amount=loan.amount_approved,
                status='ACTIVE',
                expiry_date=timezone.now() + timedelta(days=30)
            )
        
        try:
            loan_token = await create_token()
            # Update loan status
            @sync_to_async
            def update_loan():
                loan.disbursement_status = 'COMPLETED'
                loan.momo_reference = token
                loan.save()
            
            await update_loan()
            
            # Notify farmer
            await self.sms_service.send_sms(
                loan.farmer.phone_number,
                f"Your loan of {loan.amount_approved} RWF has been approved and tokenized. "
                f"Your token is {token}. Use this token at any of our certified input suppliers "
                f"to purchase agricultural inputs. The token is valid for 30 days."
            )
            
            return True, loan_token
            
        except Exception as e:
            return False, str(e)
    
    async def process_token_redemption(self, token_code, vendor_id, amount):
        """Process a token redemption at an approved vendor"""
        # Verify token is valid
        @sync_to_async
        def get_token():
            try:
                return LoanToken.objects.select_related('loan__farmer').get(
                    token=token_code,
                    status='ACTIVE',
                    amount__gte=amount
                )
            except LoanToken.DoesNotExist:
                return None
            
        @sync_to_async
        def get_vendor():
            try:
                return ApprovedVendor.objects.get(id=vendor_id, is_active=True)
            except ApprovedVendor.DoesNotExist:
                return None
        
        loan_token = await get_token()
        if not loan_token:
            return False, "Invalid or insufficient token"
        
        vendor = await get_vendor()
        if not vendor:
            return False, "Vendor not approved"
        
        # Process payment to vendor
        success, result = await self.momo_api.initiate_disbursement(
            loan_id=loan_token.loan.id,
            amount=amount,
            phone_number=vendor.phone_number
        )
        
        if not success:
            return False, "Payment failed"
        
        reference = result if isinstance(result, str) else "TOKEN-PAYMENT"
        
        # Update token amount
        @sync_to_async
        def update_token():
            with transaction.atomic():
                loan_token.amount -= amount
                if loan_token.amount <= 0:
                    loan_token.status = 'USED'
                loan_token.save()
                
                # Record transaction
                TokenTransaction.objects.create(
                    token=loan_token,
                    vendor=vendor,
                    amount=amount,
                    reference=reference
                )
        
        await update_token()
        
        # Notify farmer
        await self.sms_service.send_sms(
            loan_token.loan.farmer.phone_number,
            f"Your token has been used to purchase {amount} RWF of agricultural inputs from {vendor.name}. "
            f"Remaining token balance: {loan_token.amount} RWF."
        )
        
        return True, "Transaction successful"