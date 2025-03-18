import asyncio
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import sync_to_async
from .models import Loan, PaymentSchedule
from .sms_service import SMSService
from django.db.models import Sum  

class NotificationService:
    def __init__(self):
        self.sms_service = SMSService()
    
    async def send_payment_reminder(self, schedule):
        """Send payment reminder to farmer"""
        try:
            @sync_to_async
            def get_schedule_details():
                return {
                    'amount': schedule.amount,
                    'due_date': schedule.due_date,
                    'loan_id': schedule.loan.id,
                    'phone_number': schedule.loan.farmer.phone_number
                }
            
            details = await get_schedule_details()
            days_until_due = (details['due_date'] - timezone.now()).days
            
            message = (
                f"REMINDER: Your loan payment of {details['amount']} RWF is due in {days_until_due} days "
                f"({details['due_date'].strftime('%d-%b-%Y')}). "
                f"Loan ID: {details['loan_id']}"
            )
            
            return await self.sms_service.send_sms(
                details['phone_number'],
                message
            )
        except Exception as e:
            print(f"Failed to send payment reminder: {e}")
            return False
    

    async def send_payment_receipt(self, payment):
        """Send payment receipt to farmer"""
        try:
            @sync_to_async
            def get_payment_details():
                return {
                    'amount': payment.amount,
                    'loan_id': payment.loan.id,
                    'phone_number': payment.loan.farmer.phone_number,
                    'total_paid': payment.loan.repayments.filter(status='COMPLETED').aggregate(
                        total=Sum('amount'))['total'] or 0,
                    'amount_approved': payment.loan.amount_approved
                }
            
            details = await get_payment_details()
            remaining = details['amount_approved'] - details['total_paid']
            
            message = (
                f"PAYMENT RECEIVED: Thank you for your payment of {details['amount']} RWF. "
                f"Remaining balance: {remaining} RWF. "
                f"Loan ID: {details['loan_id']}"
            )
            
            return await self.sms_service.send_sms(
                details['phone_number'],
                message
            )
        except Exception as e:
            print(f"Failed to send payment receipt: {e}")
            return False

    async def send_loan_disbursement_notification(self, loan):
        """Send loan disbursement notification"""
        try:
            @sync_to_async
            def get_loan_details():
                return {
                    'amount': loan.amount_approved,
                    'id': loan.id,
                    'phone_number': loan.farmer.phone_number
                }
            
            details = await get_loan_details()
            
            message = (
                f"LOAN DISBURSED: Your loan of {details['amount']} RWF has been disbursed. "
                f"Please check your mobile money account. "
                f"Loan ID: {details['id']}"
            )
            
            return await self.sms_service.send_sms(
                details['phone_number'],
                message
            )
        except Exception as e:
            print(f"Failed to send disbursement notification: {e}")
            return False
        
    async def send_overdue_notification(self, loan, schedule):
        """Send overdue payment notification"""
        try:
            @sync_to_async
            def get_details():
                return {
                    'amount': schedule.amount,
                    'due_date': schedule.due_date,
                    'loan_id': loan.id,
                    'phone_number': loan.farmer.phone_number
                }
            
            details = await get_details()
            days_overdue = (timezone.now() - details['due_date']).days
            
            message = (
                f"PAYMENT OVERDUE: Your payment of {details['amount']} RWF is {days_overdue} days overdue. "
                f"Please make payment to avoid penalties. "
                f"Loan ID: {details['loan_id']}"
            )
            
            # Save that we attempted to send notification regardless of SMS outcome
            @sync_to_async
            def mark_as_sent():
                schedule.overdue_notification_sent = True
                schedule.save()
                
            # Send SMS
            sms_result, _ = await self.sms_service.send_sms(
                details['phone_number'],
                message
            )
            
            # Mark as sent even if SMS failed (to prevent repeated attempts)
            await mark_as_sent()
            
            return sms_result
        except Exception as e:
            print(f"Failed to send overdue notification: {e}")
            return False
        
    async def send_loan_completion_notification(self, loan):
        """Send loan completion notification"""
        try:
            @sync_to_async
            def get_loan_details():
                return {
                    'amount': loan.amount_approved,
                    'id': loan.id,
                    'phone_number': loan.farmer.phone_number
                }
            
            loan_details = await get_loan_details()
            
            message = (
                f"LOAN COMPLETED: Congratulations! Your loan of {loan_details['amount']} RWF "
                f"has been fully repaid. Thank you for your business. "
                f"Loan ID: {loan_details['id']}"
            )
            
            return await self.sms_service.send_sms(
                loan_details['phone_number'],
                message
            )
        except Exception as e:
            print(f"Failed to send completion notification: {e}")
            return False

    async def send_daily_reminders(self):
        """Send reminders for payments due soon"""
        current_date = timezone.now()
        
        @sync_to_async
        def get_upcoming_schedules():
            # Get schedules due in the next 3 days
            return list(PaymentSchedule.objects.filter(
                status='PENDING',
                due_date__range=[current_date, current_date + timedelta(days=3)]
            ).select_related('loan__farmer'))
        
        @sync_to_async
        def get_overdue_schedules():
            # Get schedules that are overdue but notification not sent
            return list(PaymentSchedule.objects.filter(
                status='PENDING',
                due_date__lt=current_date,
                overdue_notification_sent=False
            ).select_related('loan__farmer'))
        
        # Send reminders for upcoming payments
        upcoming_schedules = await get_upcoming_schedules()
        for schedule in upcoming_schedules:
            await self.send_payment_reminder(schedule)
            
        # Send notifications for overdue payments
        overdue_schedules = await get_overdue_schedules()
        for schedule in overdue_schedules:
            await self.send_overdue_notification(schedule.loan, schedule)
            
            @sync_to_async
            def mark_sent():
                schedule.overdue_notification_sent = True
                schedule.save()
            
            await mark_sent()