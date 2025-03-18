from django.utils import timezone
from asgiref.sync import sync_to_async
from django.db import transaction
from .models import Loan
from .repayment_service import RepaymentService
from .notification_service import NotificationService
from .momo_integration import MoMoAPI
from datetime import timedelta  
from .services import LoanService
from .sms_service import SMSService

class LoanLifecycleService:
    """Service to manage the complete lifecycle of a loan"""
    
    def __init__(self):
        self.repayment_service = RepaymentService()
        self.notification_service = NotificationService()
        self.momo_api = MoMoAPI()
        self.sms_service = SMSService() 

    async def approve_loan(self, loan_id, approved_amount=None):
        """Approve a loan application"""
        try:
            @sync_to_async
            def get_and_update_loan():
                with transaction.atomic():
                    try:
                        loan = Loan.objects.select_for_update().get(id=loan_id)
                        
                        if loan.status != 'PENDING':
                            return None, "Loan is not in PENDING status"
                        
                        loan.status = 'APPROVED'
                        loan.approval_date = timezone.now()
                        
                        if approved_amount is not None:
                            loan.amount_approved = approved_amount
                        else:
                            loan.amount_approved = loan.amount_requested
                            
                        loan.save()
                        
                        # Get the farmer's phone number while we're in the sync context
                        phone_number = loan.farmer.phone_number
                        amount = loan.amount_approved
                        
                        return loan, None, phone_number, amount
                    except Loan.DoesNotExist:
                        return None, "Loan not found", None, None
                    except Exception as e:
                        return None, str(e), None, None
            
            loan, error, phone_number, amount = await get_and_update_loan()
            
            if error:
                return False, error
            
            if not loan:
                return False, "Could not approve loan"
            
            # Send approval notification
            try:
                message = (
                    f"Your loan application for {amount} RWF has been approved! "
                    f"Funds will be disbursed shortly."
                )
                await self.sms_service.send_sms(phone_number, message)
            except Exception as e:
                # Log the error but don't fail the approval
                print(f"SMS notification failed: {e}")
            
            return True, loan
        
        except Exception as e:
            return False, f"Error approving loan: {str(e)}"
    async def disburse_loan(self, loan_id):
        """Disburse an approved loan"""
        try:
            @sync_to_async
            def get_loan():
                return Loan.objects.get(id=loan_id)
            
            loan = await get_loan()
            
            if loan.status != 'APPROVED':
                return False, "Loan must be in APPROVED status to disburse"
            
            # Initiate mobile money transfer
            success, result = await self.momo_api.disburse(
                loan.farmer.phone_number,
                loan.amount_approved,
                f"Loan disbursement for {loan.id}"
            )
            
            if not success:
                return False, f"Failed to disburse loan: {result}"
            
            # Update loan status
            @sync_to_async
            def update_loan():
                with transaction.atomic():
                    loan.status = 'DISBURSED'
                    loan.disbursement_date = timezone.now()
                    # Calculate due date based on loan product duration
                    loan.due_date = timezone.now() + timedelta(days=loan.loan_product.duration_days)
                    loan.save()
                    return loan
            
            updated_loan = await update_loan()
            
            # Create payment schedule
            loan_service = LoanService()
            await loan_service.create_payment_schedule(updated_loan)
            
            # Send disbursement notification
            await self.notification_service.send_loan_disbursement_notification(updated_loan)
            
            return True, updated_loan
            
        except Exception as e:
            return False, f"Error disbursing loan: {str(e)}"
    
    async def complete_loan_process(self, loan_id):
        """Handle a fully repaid loan"""
        try:
            @sync_to_async
            def get_and_update_loan():
                with transaction.atomic():
                    try:
                        loan = Loan.objects.select_for_update().get(id=loan_id)
                        
                        # If already paid, consider it a success instead of an error
                        if loan.status == 'PAID':
                            print(f"[DEBUG] Loan {loan_id} is already marked as PAID")
                            return loan, None
                        
                        # Verify all schedules are paid
                        unpaid = loan.paymentschedule_set.filter(
                            status__in=['PENDING', 'PARTIAL']
                        ).exists()
                        
                        if unpaid:
                            return None, "Loan has unpaid schedules"
                        
                        print(f"[DEBUG] Marking loan {loan_id} as PAID")
                        loan.status = 'PAID'
                        loan.completion_date = timezone.now()
                        loan.save()
                        return loan, None
                    except Loan.DoesNotExist:
                        return None, "Loan not found"
                    except Exception as e:
                        return None, str(e)
            
            loan, error = await get_and_update_loan()
            if error:
                return False, error
                
            if not loan:
                return False, "Could not complete loan"
            
            # Send completion notification
            try:
                await self.notification_service.send_loan_completion_notification(loan)
            except Exception as e:
                print(f"SMS notification failed: {e}")
                # Don't fail the completion just because SMS failed
            
            return True, "Loan marked as completed"
            
        except Exception as e:
            return False, f"Error completing loan: {str(e)}"