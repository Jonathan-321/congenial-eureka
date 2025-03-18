# backend/loans/climate_services.py

from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from asgiref.sync import sync_to_async
from .models import Loan, PaymentSchedule
from .external.weather_api import WeatherService
from .services import SMSService

class ClimateAdaptiveLoanService:
    def __init__(self):
        self.weather_service = WeatherService()
        self.sms_service = SMSService()
    
    async def check_for_adverse_conditions(self):
        """Check for adverse weather conditions and adjust loan schedules"""
        # Get all active loans
        @sync_to_async
        def get_active_loans():
            return list(Loan.objects.filter(
                status='APPROVED',
                disbursement_status='COMPLETED'
            ).select_related('farmer'))
        
        loans = await get_active_loans()
        
        for loan in loans:
            # Check weather conditions in farmer's region
            conditions = await self.weather_service.get_conditions(loan.farmer.location)
            
            if conditions.get('drought_index', 0) > 0.7 or conditions.get('flood_index', 0) > 0.7:
                # Get upcoming payment schedules
                @sync_to_async
                def get_upcoming_payments():
                    return list(PaymentSchedule.objects.filter(
                        loan=loan,
                        status='PENDING',
                        due_date__lte=timezone.now() + timedelta(days=30)
                    ))
                
                schedules = await get_upcoming_payments()
                
                if not schedules:
                    continue
                
                # Extend payment deadlines
                @sync_to_async
                def extend_payments():
                    with transaction.atomic():
                        for schedule in schedules:
                            schedule.due_date = schedule.due_date + timedelta(days=30)
                            schedule.save()
                
                await extend_payments()
                
                # Notify farmer
                await self.sms_service.send_sms(
                    loan.farmer.phone_number,
                    f"Due to adverse weather conditions in your area, your upcoming loan "
                    f"payment has been automatically extended by 30 days. No action is required."
                )
                
                # Log the adjustment
                print(f"Extended payment deadlines for loan {loan.id} due to adverse weather")