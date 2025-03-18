from backend.celery import app as celery_app
from asgiref.sync import sync_to_async
from .models import Transaction, Loan
from .services import LoanService
from django.conf import settings
import asyncio
from .services import PaymentScheduleService


@celery_app.task
async def monitor_payment_status(transaction_reference: str, max_attempts: int = 5):
    """
    Monitor payment status for a given transaction
    """
    from .momo_integration import MoMoAPI
    from .services import PaymentScheduleService

    payment_service = PaymentScheduleService()
    await payment_service.check_overdue_payments()
    await payment_service.send_upcoming_reminders()

    momo = MoMoAPI()
    loan_service = LoanService()
    attempt = 0
    
    while attempt < max_attempts:
        try:
            status = await momo.check_payment_status(transaction_reference)
            
            if status.get('status') == 'SUCCESSFUL':
                # Get transaction details
                transaction = await Transaction.objects.aget(reference=transaction_reference)
                
                # Record the payment
                await loan_service.record_repayment(
                    loan_id=transaction.loan.id,
                    amount=transaction.amount,
                    momo_reference=transaction_reference
                )
                return True
                
            elif status.get('status') == 'FAILED':
                return False
                
            attempt += 1
            await asyncio.sleep(settings.PAYMENT_CHECK_INTERVAL)
            
        except Exception as e:
            print(f"Error checking payment status: {str(e)}")
            return False
            
    return False


# Modify the task in loans/tasks.py

@celery_app.task
async def check_schedules_and_send_reminders():
    """Check payment schedules and send reminders"""
    payment_service = PaymentScheduleService()
    
    # Check for overdue payments
    await payment_service.check_overdue_payments()
    
    # Send regular reminders
    await payment_service.send_upcoming_reminders()
    
    # Send harvest-based reminders
    await payment_service.send_harvest_based_reminders()
    
    return True