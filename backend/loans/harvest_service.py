# backend/loans/harvest_service.py

from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from decimal import Decimal
from .models import Loan, CropCycle, HarvestBasedPaymentSchedule, HarvestPaymentInstallment
from .services import SMSService

class HarvestBasedLoanService:
    def __init__(self):
        self.sms_service = SMSService()
    
    @sync_to_async
    def get_farmer_crop_cycles(self, farmer, active_only=True):
        """Get crop cycles for a farmer, optionally only active ones"""
        queryset = CropCycle.objects.filter(farmer=farmer)
        if active_only:
            today = timezone.now().date()
            queryset = queryset.filter(expected_harvest_date__gte=today)
        return list(queryset)
    
    async def create_harvest_based_schedule(self, loan, crop_cycle):
        """Create a payment schedule based on harvest dates"""
        # Calculate days between now and harvest
        today = timezone.now().date()
        days_to_harvest = (crop_cycle.expected_harvest_date - today).days
        
        # Don't create a schedule if harvest is too soon
        if days_to_harvest < 15:
            return False, "Harvest date too close for loan repayment"
        
        # Calculate installment amounts
        # Example: 70% due after harvest, 30% due 30 days after harvest
        principal = loan.amount_approved
        interest = principal * (loan.loan_product.interest_rate / 100)
        total_due = principal + interest
        
        harvest_payment = total_due * Decimal('0.7')
        final_payment = total_due - harvest_payment
        
        @sync_to_async
        def create_schedule():
            with transaction.atomic():
                # Create the schedule
                schedule = HarvestBasedPaymentSchedule.objects.create(
                    loan=loan,
                    crop_cycle=crop_cycle
                )
                
                # Create the installments
                HarvestPaymentInstallment.objects.create(
                    schedule=schedule,
                    due_date=crop_cycle.expected_harvest_date + timedelta(days=7),
                    amount=harvest_payment,
                    percentage_of_harvest=Decimal('0.7')
                )
                
                HarvestPaymentInstallment.objects.create(
                    schedule=schedule,
                    due_date=crop_cycle.expected_harvest_date + timedelta(days=30),
                    amount=final_payment,
                    percentage_of_harvest=Decimal('0.3')
                )
                
                # Update loan due date
                loan.due_date = crop_cycle.expected_harvest_date + timedelta(days=30)
                loan.save()
                
                return schedule
        
        try:
            schedule = await create_schedule()
            
            # Notify farmer
            await self.sms_service.send_sms(
                loan.farmer.phone_number,
                f"Your loan repayment schedule has been created based on your expected harvest date "
                f"({crop_cycle.expected_harvest_date.strftime('%d-%b-%Y')}). "
                f"First payment of {harvest_payment} RWF is due one week after harvest."
            )
            
            return True, schedule
        except Exception as e:
            return False, str(e)
    
    async def adjust_schedule_for_weather(self, schedule, delay_days):
        """Adjust payment schedule based on weather events"""
        @sync_to_async
        def update_schedule():
            with transaction.atomic():
                # Update all installments
                for installment in schedule.installments.all():
                    installment.due_date = installment.due_date + timedelta(days=delay_days)
                    installment.save()
                
                # Update the loan due date
                loan = schedule.loan
                loan.due_date = loan.due_date + timedelta(days=delay_days)
                loan.save()
                
                return schedule
        
        try:
            updated_schedule = await update_schedule()
            
            # Notify farmer
            await self.sms_service.send_sms(
                schedule.loan.farmer.phone_number,
                f"Due to weather conditions, your loan repayment dates have been adjusted. "
                f"Your new payment dates have been extended by {delay_days} days."
            )
            
            return True, updated_schedule
        except Exception as e:
            return False, str(e)