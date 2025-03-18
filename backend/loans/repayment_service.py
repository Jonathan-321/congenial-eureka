from decimal import Decimal
from email import message
from django.utils import timezone
from asgiref.sync import sync_to_async
from django.db import transaction
from .models import Loan, LoanRepayment, PaymentSchedule
from .momo_integration import MoMoAPI
from .sms_service import SMSService
from django.db import models
from django.db.models import Sum

class RepaymentService:
    def __init__(self):
        self.momo_api = MoMoAPI()
        self.sms_service = SMSService()

    async def process_payment(self, payment_data):
        """Process a loan repayment"""
        try:
            print(f"[DEBUG] Starting payment processing: {payment_data}")
            reference = payment_data.get('reference')
            payment_amount = Decimal(payment_data.get('amount'))
            phone_number = payment_data.get('phone_number')
            
            if not reference or not payment_amount or not phone_number:
                return False, "Missing required payment data"
            
            @sync_to_async
            def get_loan_and_process():
                try:
                    with transaction.atomic():
                        loan = Loan.objects.select_for_update().get(id=reference)
                        
                        print(f"[DEBUG] Current loan status: {loan.status}")
                        
                        # If loan is already PAID, return success with message
                        if loan.status == 'PAID':
                            return {'already_paid': True}, "Loan was already paid"
                        
                        print(f"[DEBUG] Starting to record repayment: loan={loan.id}, amount={payment_amount}")
                        
                        # Create repayment record
                        repayment = LoanRepayment.objects.create(
                            loan=loan,
                            amount=payment_amount,
                            payment_date=timezone.now(),
                            transaction_reference=f"PAYMENT-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                        )
                        
                        # Update payment schedule if applicable
                        schedules = loan.payment_schedules.filter(
                            status__in=['PENDING', 'PARTIAL']
                        ).order_by('due_date')
                        
                        remaining_amount = payment_amount
                        total_repaid = loan.repayments.aggregate(
                            total=Sum('amount'))['total'] or 0
                        
                        # Process each payment schedule
                        for schedule in schedules:
                            if remaining_amount <= 0:
                                break
                                
                            amount_due = schedule.amount - schedule.amount_paid
                            
                            if remaining_amount >= amount_due:
                                # Full payment for this schedule
                                schedule.amount_paid += amount_due
                                schedule.status = 'PAID'
                                schedule.payment_date = timezone.now()
                                remaining_amount -= amount_due
                            else:
                                # Partial payment
                                schedule.amount_paid += remaining_amount
                                schedule.status = 'PARTIAL'
                                remaining_amount = 0
                                
                            schedule.save()
                        
                        # Calculate new total after this payment
                        new_total_paid = total_repaid + payment_amount
                        
                        # Update loan status
                        loan_status = 'ACTIVE'
                        if new_total_paid >= loan.amount_approved:
                            loan.status = 'PAID'
                            loan_status = 'PAID'
                        elif loan.status == 'OVERDUE':
                            loan.status = 'ACTIVE'
                        
                        loan.save()
                        
                        return {
                            'loan': loan,
                            'repayment': repayment,
                            'total_repaid': new_total_paid,
                            'status': loan_status,
                            'payment_amount': payment_amount,
                            'phone_number': loan.farmer.phone_number,
                            'amount_approved': loan.amount_approved,
                            'remaining_balance': max(loan.amount_approved - new_total_paid, 0)
                        }, None
                        
                except Loan.DoesNotExist:
                    return None, f"Loan with reference {reference} not found"
                except Exception as e:
                    print(f"Error processing payment: {str(e)}")
                    return None, str(e)

            result, error_message = await get_loan_and_process()
            
            # Handle already paid loans as a success case
            if result and result.get('already_paid'):
                return True, error_message
            
            if not result:
                return False, error_message
            
            # Send SMS notifications
            try:
                if result['status'] == 'PAID':
                    await self.sms_service.send_sms(
                        result['phone_number'],
                        f"Congratulations! Your loan of {result['amount_approved']} RWF has been fully repaid."
                    )
                else:
                    await self.sms_service.send_sms(
                        result['phone_number'],
                        f"Payment of {result['payment_amount']} RWF received. Remaining balance: {result['remaining_balance']} RWF"
                    )
            except Exception as e:
                print(f"SMS notification failed: {e}")
                # Don't fail the repayment just because SMS failed
            
            return True, "Repayment processed successfully"
            
        except Exception as e:
            print(f"Payment processing error: {str(e)}")
            return False, str(e)


    async def record_repayment(self, loan, amount, reference):
        """Record a loan repayment and update payment schedules"""
        try:
            @sync_to_async
            def create_repayment():
                with transaction.atomic():
                    # Create repayment record
                    repayment = LoanRepayment.objects.create(
                        loan=loan,
                        amount=amount,
                        reference=reference,
                        payment_date=timezone.now(),
                        status='COMPLETED'
                    )
                    
                    # Update payment schedules - pay oldest due schedule first
                    remaining = amount
                    schedules = PaymentSchedule.objects.filter(
                        loan=loan, 
                        status='PENDING'
                    ).order_by('due_date')
                    
                    for schedule in schedules:
                        if remaining <= 0:
                            break
                            
                        if remaining >= schedule.amount:
                            schedule.amount_paid = schedule.amount
                            schedule.status = 'PAID'
                            schedule.payment_date = timezone.now()
                            remaining -= schedule.amount
                        else:
                            schedule.amount_paid = remaining
                            schedule.status = 'PARTIAL'
                            schedule.payment_date = timezone.now()
                            remaining = 0
                            
                        schedule.save()
                    
                    return repayment
            
            repayment = await create_repayment()
            return True, repayment
            
        except Exception as e:
            return False, f"Error recording repayment: {str(e)}"
    
    async def get_remaining_balance(self, loan):
        """Get remaining balance on a loan"""
        @sync_to_async
        def calculate_balance():
            total_paid = loan.repayments.filter(status='COMPLETED').aggregate(
                total=models.Sum('amount'))['total'] or 0
            return max(loan.amount_approved - total_paid, 0)
        
        return await calculate_balance()

    async def update_loan_status(self, loan):
        """Update loan status based on payments"""
        @sync_to_async
        def update_status():
            with transaction.atomic():
                # Skip if already paid
                if loan.status == 'PAID':
                    return loan
                    
                # Check if loan is fully paid
                total_paid = loan.repayments.aggregate(
                    total=models.Sum('amount'))['total'] or 0
                
                if total_paid >= loan.amount_approved:
                    loan.status = 'PAID'
                elif loan.status == 'OVERDUE':
                    # Check if this payment covers the overdue amount
                    loan.status = 'ACTIVE'
                
                loan.save()
                return loan
        
        return await update_status()