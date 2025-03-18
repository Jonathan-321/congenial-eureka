from decimal import Decimal
from datetime import datetime, timedelta
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
import httpx
import uuid

from farmers.models import Farmer
from .models import Loan, LoanRepayment, PaymentSchedule, LoanProduct
from .momo_integration import MoMoAPI
from .sms_service import SMSService  # Import from dedicated file
from asgiref.sync import sync_to_async
from .models import CropCycle


class AfricasTalkingService:
    def __init__(self):
        self.username = settings.AT_USERNAME
        self.api_key = settings.AT_API_KEY
        self.base_url = 'https://api.sandbox.africastalking.com'

    async def check_wallet_balance(self):
        """Check AT wallet balance"""
        url = f"{self.base_url}/version1/user?username={self.username}"
        headers = {
            'ApiKey': self.api_key,
            'Accept': 'application/json'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            return response.json()

    async def request_data_bundle(self, phone_number, amount):
        """Request data bundle for a user"""
        url = f"{self.base_url}/mobile/data/request"
        headers = {
            'ApiKey': self.api_key,
            'Content-Type': 'application/json'
        }
        
        data = {
            'username': self.username,
            'phoneNumber': phone_number,
            'amount': amount
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)
            return response.json()


class PaymentScheduleService:
    def __init__(self):
        self.sms_service = SMSService()

    async def check_overdue_payments(self):
        """Check for overdue payments and update status"""
        current_date = timezone.now()
        
        @sync_to_async
        def get_overdue_schedules():
            return list(PaymentSchedule.objects.filter(
                status='PENDING',
                due_date__lt=current_date
            ).select_related('loan__farmer'))
        
        overdue_schedules = await get_overdue_schedules()
        
        for schedule in overdue_schedules:
            days_overdue = (current_date - schedule.due_date).days
            if days_overdue > 0:
                # Update status to overdue
                schedule.status = 'OVERDUE'
                # Calculate penalty (1% per day overdue, max 30%)
                daily_rate = Decimal('0.01')  # 1% per day
                penalty = schedule.amount * min(daily_rate * days_overdue, Decimal('0.3'))
                schedule.penalty_amount = penalty
                await schedule.asave()
                
                # Send reminder if none sent in last 24 hours
                if (not schedule.last_reminder_sent or 
                    current_date - schedule.last_reminder_sent > timedelta(days=1)):
                    await self.sms_service.send_sms(
                        schedule.loan.farmer.phone_number,
                        f"REMINDER: Your loan payment of {schedule.amount} is {days_overdue} days overdue. " +
                        f"Current amount due with penalty: {schedule.amount + penalty}. " +
                        "Please make payment to avoid additional penalties."
                    )
                    schedule.last_reminder_sent = current_date
                    await schedule.asave()

    async def send_upcoming_reminders(self):
        """Send reminders for upcoming payments"""
        current_date = timezone.now()
        reminder_days = [7, 3, 1]  # Remind 7 days, 3 days, and 1 day before due date
        
        for days in reminder_days:
            target_date = current_date + timedelta(days=days)
            upcoming_schedules = await PaymentSchedule.objects.filter(
                status='PENDING',
                due_date__date=target_date.date()
            ).select_related('loan__farmer').all()
            
            for schedule in upcoming_schedules:
                await self.sms_service.send_sms(
                    schedule.loan.farmer.phone_number,
                    f"REMINDER: Your loan payment of {schedule.amount} is due in {days} " +
                    f"{'day' if days == 1 else 'days'}. " +
                    "Please ensure funds are available in your mobile money account."
                )

    async def apply_payment(self, loan: Loan, amount: Decimal) -> dict:
        """Apply payment to pending schedules"""
        remaining_amount = amount
        applied_to = []
        
        # Wrap the queryset operation with sync_to_async
        @sync_to_async
        def get_pending_schedules():
            return list(PaymentSchedule.objects.filter(
                loan=loan,
                status__in=['PENDING', 'OVERDUE', 'PARTIALLY_PAID']
            ).order_by('due_date'))
        
        # Get the schedules asynchronously
        schedules = await get_pending_schedules()
        
        for schedule in schedules:
            if remaining_amount <= 0:
                break
                
            # Calculate total due (including any penalties)
            total_due = schedule.amount + schedule.penalty_amount - schedule.amount_paid
            
            if remaining_amount >= total_due:
                # Full payment
                schedule.amount_paid += total_due
                schedule.status = 'PAID'
                remaining_amount -= total_due
                applied_to.append({
                    'installment': schedule.installment_number,
                    'amount': total_due,
                    'status': 'PAID'
                })
            else:
                # Partial payment
                schedule.amount_paid += remaining_amount
                schedule.status = 'PARTIALLY_PAID'
                applied_to.append({
                    'installment': schedule.installment_number,
                    'amount': remaining_amount,
                    'status': 'PARTIALLY_PAID'
                })
                remaining_amount = 0
                
            await schedule.asave()
            
        return {
            'applied_to': applied_to,
            'remaining': remaining_amount
        }
    # Add to PaymentScheduleService in loans/services.py

    async def send_harvest_based_reminders(self):
        """Send reminders for upcoming payments with harvest context"""
        current_date = timezone.now()
        
        @sync_to_async
        def get_upcoming_harvest_schedules():
            # Get loans with harvest-based repayment
            harvest_loans = Loan.objects.filter(
                loan_product__repayment_schedule_type='HARVEST'
            ).values_list('id', flat=True)
            
            # Get schedules for these loans
            return list(PaymentSchedule.objects.filter(
                loan_id__in=harvest_loans,
                status='PENDING',
                due_date__range=[current_date, current_date + timedelta(days=14)]
            ).select_related('loan__farmer'))
        
        schedules = await get_upcoming_harvest_schedules()
        
        for schedule in schedules:
            # Find the closest harvest date
            @sync_to_async
            def get_closest_harvest():
                return CropCycle.objects.filter(
                    farmer=schedule.loan.farmer,
                    expected_harvest_date__lte=schedule.due_date
                ).order_by('-expected_harvest_date').first()
            
            harvest_cycles = await get_closest_harvest()
            
            if harvest_cycles:
                days_after_harvest = (schedule.due_date - harvest_cycles.expected_harvest_date).days
                crop_type = harvest_cycles.get_crop_type_display()
                
                await self.sms_service.send_sms(
                    schedule.loan.farmer.phone_number,
                    f"REMINDER: Your loan payment of {schedule.amount} is due on "
                    f"{schedule.due_date.strftime('%d %b %Y')}, which is {days_after_harvest} days "
                    f"after your expected {crop_type} harvest. Please plan accordingly."
                )

class LoanService:
    def __init__(self):
        self.momo_api = MoMoAPI()
        self.sms_service = SMSService()

    async def create_payment_schedule(self, loan: Loan) -> None:
        """Create payment schedule for a loan"""
        # Calculate number of months based on duration_days
        num_months = loan.loan_product.duration_days // 30
        
        amount_per_payment = loan.amount_approved / num_months
        interest_rate = loan.loan_product.interest_rate / 100 / 12  # Monthly interest
        
        current_date = loan.disbursement_date or timezone.now()
        remaining_balance = loan.amount_approved
        
        schedules = []
        for month in range(1, num_months + 1):
            interest_amount = remaining_balance * interest_rate
            principal_amount = amount_per_payment
            total_amount = principal_amount + interest_amount
            
            due_date = current_date + timedelta(days=30)
            
            schedules.append(PaymentSchedule(
                loan=loan,
                installment_number=month,
                due_date=due_date,
                principal_amount=principal_amount,
                interest_amount=interest_amount,
                amount=total_amount,
                status='PENDING'
            ))
            
            remaining_balance -= principal_amount
            current_date = due_date

        # Wrap the bulk_create in a transaction and properly handle async/sync
        @sync_to_async
        def create_schedules_sync():
            with transaction.atomic():
                PaymentSchedule.objects.bulk_create(schedules)
                
        await create_schedules_sync()

    async def check_loan_status(self, loan: Loan) -> None:
        """Check and update loan status based on payments and due dates"""
        total_paid = await self.get_loan_balance(loan)
        current_schedule = await PaymentSchedule.objects.filter(
            loan=loan,
            due_date__lte=timezone.now(),
            status='PENDING'
        ).afirst()
        
        if total_paid >= loan.amount_approved:
            loan.status = 'PAID'
        elif current_schedule and current_schedule.due_date < timezone.now():
            loan.status = 'OVERDUE'
            # Send overdue notification
            await self.sms_service.send_sms(
                loan.farmer.phone_number,
                f"Your loan payment of {current_schedule.total_amount} EUR is overdue. Please make payment to avoid penalties."
            )
        else:
            loan.status = 'ACTIVE'
            
        await loan.asave()

    # Assuming this is the method being called in the test
    async def apply_for_loan(farmer_id, loan_product_id, amount):
        try:
            farmer = await sync_to_async(Farmer.objects.get)(id=farmer_id)
            loan_product = await sync_to_async(LoanProduct.objects.get)(id=loan_product_id)
            
            # Validate amount
            if amount < loan_product.min_amount or amount > loan_product.max_amount:
                return False
                
            # Create a loan application
            loan = await sync_to_async(Loan.objects.create)(
                farmer=farmer,
                loan_product=loan_product,
                amount_requested=amount,
                status='PENDING'
            )
            
            # Return True for successful loan application
            return True
        except Exception as e:
            # Log the exception
            print(f"Error applying for loan: {e}")
            return False

    # Add to LoanService class
    async def record_repayment(self, loan_id: uuid.UUID, amount: Decimal, momo_reference: str) -> dict:
        try:
            async with transaction.atomic():
                loan = await Loan.objects.aget(id=loan_id)
                
                # Create repayment record
                await LoanRepayment.objects.acreate(
                    loan=loan,
                    amount=amount,
                    transaction_reference=momo_reference
                )

                # Apply payment to specific installments
                payment_service = PaymentScheduleService()
                payment_allocation = await payment_service.apply_payment(loan, amount)
                
                # Update loan status
                total_repaid = await self.get_loan_balance(loan)
                
                if total_repaid >= loan.amount_approved:
                    loan.status = 'PAID'
                    # Send completion SMS
                    await self.sms_service.send_sms(
                        loan.farmer.phone_number,
                        f"Congratulations! Your loan of {loan.amount_approved} has been fully repaid."
                    )
                else:
                    await self.check_loan_status(loan)
                    # Send confirmation SMS
                    await self.sms_service.send_sms(
                        loan.farmer.phone_number,
                        f"Payment of {amount} received. Thank you!"
                    )
                
                return {
                    'status': 'SUCCESS',
                    'payment_allocation': payment_allocation,
                    'loan_status': loan.status
                }

        except Exception as e:
            return {'status': 'ERROR', 'message': str(e)}

    @staticmethod
    async def get_loan_balance(loan) -> Decimal:
        """Calculate current loan balance"""
        total_repaid = await LoanRepayment.objects.filter(loan=loan).aggregate(
            total=models.Sum('amount')
        )
        return max(loan.amount_approved - (total_repaid['total'] or 0), 0)

    @staticmethod
    def calculate_credit_score(farmer):
        """
        Calculate credit score based on farmer's history and data
        Returns a score between 0 and 100
        """
        base_score = 50
        
        # Factor in previous loans
        previous_loans = Loan.objects.filter(farmer=farmer)
        if previous_loans.exists():
            # Reward for paid loans
            paid_loans = previous_loans.filter(status='PAID').count()
            base_score += min(paid_loans * 10, 30)  # Max 30 points from paid loans
            
            # Penalize for defaulted loans
            defaulted_loans = previous_loans.filter(status='DEFAULTED').count()
            base_score -= min(defaulted_loans * 20, 40)  # Max 40 points penalty
            
            # Consider payment timeliness
            on_time_payments = LoanRepayment.objects.filter(
                loan__in=previous_loans,
                payment_date__lte=models.F('loan__due_date')
            ).count()
            base_score += min(on_time_payments * 5, 15)  # Max 15 points for timeliness
        
        # Factor in farm size (larger farms get slightly higher scores)
        base_score += min(farmer.farm_size * 2, 20)
        
        # Ensure score is between 0 and 100
        return min(max(base_score, 0), 100)

    @staticmethod
    def check_loan_eligibility(farmer, loan_product, amount):
        """Check if farmer is eligible for requested loan"""
        if amount < loan_product.min_amount or amount > loan_product.max_amount:
            return False, f"Loan amount must be between {loan_product.min_amount} and {loan_product.max_amount}"
            
        if amount > loan_product.max_amount:
            return False, f"Loan amount cannot exceed {loan_product.max_amount}"

        # Check if farmer has any active loans
        active_loans = Loan.objects.filter(
            farmer=farmer,
            status__in=['PENDING', 'APPROVED', 'DISBURSED', 'ACTIVE']
        )
        if active_loans.exists():
            return False, "Farmer has existing active loans"
            
        # Calculate and check credit score
        credit_score = LoanService.calculate_credit_score(farmer)
        if credit_score < settings.MINIMUM_CREDIT_SCORE:
            return False, f"Credit score ({credit_score}) below minimum requirement"
            
        # Check total exposure
        total_exposure = Loan.objects.filter(
            farmer=farmer,
            status__in=['DISBURSED', 'ACTIVE']
        ).aggregate(total=models.Sum('amount_approved'))['total'] or 0
        
        if total_exposure + amount > settings.MAXIMUM_EXPOSURE:
            return False, "Maximum exposure limit reached"
            
        return True, "Eligible for loan"

    @staticmethod
    async def process_loan_application(farmer, loan_product, amount):
        """Process a loan application"""
        try:
            # Validate loan amount
            if amount < loan_product.min_amount or amount > loan_product.max_amount:
                return False, "Loan amount outside allowed range"
            
            # Calculate credit score and create loan
            @sync_to_async
            def calculate_score_and_create_loan():
                credit_score = LoanService.calculate_credit_score(farmer)
                
                # Create loan application
                loan = Loan.objects.create(
                    farmer=farmer,
                    loan_product=loan_product,
                    amount_requested=amount,
                    status='PENDING',
                    credit_score=credit_score
                )
                return loan, farmer.phone_number
            
            loan, phone_number = await calculate_score_and_create_loan()
            
            # Send notification
            sms_service = SMSService()
            try:
                await sms_service.send_sms(
                    phone_number,
                    f"Your loan application for {amount} RWF has been received and is being processed."
                )
            except Exception as e:
                print(f"SMS notification failed: {e}")
                # Don't fail the application just because SMS failed
            
            return True, loan
        except Exception as e:
            return False, f"Error processing loan application: {str(e)}"

    @staticmethod
    async def initiate_loan_disbursement(loan):
        """Initiate loan disbursement via MTN MoMo"""
        try:
            momo_api = MoMoAPI()
            transaction = await momo_api.initiate_disbursement(
                phone_number=loan.farmer.phone_number,
                amount=loan.amount_approved,
                reference=f"LOAN-{loan.id}"
            )
            
            loan.disbursement_status = 'PROCESSING'
            loan.momo_reference = transaction['reference']
            loan.save()
            
            # Send disbursement SMS
            await SMSService.send_sms(
                loan.farmer.phone_number,
                f"Your loan of {loan.amount_approved} RWF is being disbursed to your mobile money account."
            )
            
            return True, transaction['reference']
            
        except Exception as e:
            loan.disbursement_status = 'FAILED'
            loan.save()
            return False, str(e)

    @staticmethod
    async def process_application(loan_id: int) -> bool:
        loan = await Loan.objects.aget(id=loan_id)
        
        # Check eligibility
        if not await LoanService.check_eligibility(loan):
            return False
            
        # Initiate disbursement
        momo = MoMoAPI()
        disbursement = await momo.initiate_disbursement(
            loan_id=loan.id,
            amount=loan.amount_approved,
            phone_number=loan.farmer.phone_number
        )
        
        if disbursement['status'] == 'SUCCESSFUL':
            loan.status = 'DISBURSED'
            await loan.asave()
            return True
        return False
    
    # Add to LoanService class in loans/services.py

    async def create_harvest_based_schedule(self, loan: Loan, harvest_dates: list) -> None:
        """Create payment schedule based on expected harvest dates"""
        if not harvest_dates:
            # Fallback to regular schedule if no harvest dates provided
            return await self.create_payment_schedule(loan)
        
        # Sort harvest dates
        harvest_dates.sort()
        
        # Calculate amount per harvest
        amount_per_payment = loan.amount_approved / len(harvest_dates)
        interest_rate = loan.loan_product.interest_rate / 100 / 12  # Monthly interest
        
        # Get grace period from loan product
        grace_period = loan.loan_product.grace_period_days
        
        schedules = []
        remaining_balance = loan.amount_approved
        
        # Convert loan.disbursement_date to date object for consistent comparison
        disbursement_date = loan.disbursement_date.date() if loan.disbursement_date else timezone.now().date()
        
        for i, harvest_date in enumerate(harvest_dates, 1):
            # Calculate due date (harvest date + grace period)
            due_date = harvest_date + timedelta(days=grace_period)
            
            # Calculate interest based on time since disbursement
            days_elapsed = (due_date - disbursement_date).days
            months_elapsed = Decimal(days_elapsed) / Decimal('30')  # Convert to Decimal
            interest_amount = remaining_balance * interest_rate * months_elapsed
            
            principal_amount = amount_per_payment
            total_amount = principal_amount + interest_amount
            
            schedules.append(PaymentSchedule(
                loan=loan,
                installment_number=i,
                due_date=due_date,
                principal_amount=principal_amount,
                interest_amount=interest_amount,
                amount=total_amount,
                status='PENDING'
            ))
            
            remaining_balance -= principal_amount
        
        # Wrap the bulk_create in a transaction and properly handle async/sync
        @sync_to_async
        def create_schedules_sync():
            with transaction.atomic():
                PaymentSchedule.objects.bulk_create(schedules)
                
        await create_schedules_sync()

class LoanRepaymentService:
    def __init__(self):
        self.sms_service = SMSService()
        
    async def process_repayment(self, loan, amount, transaction_reference):
        """Process a loan repayment"""
        try:
            @sync_to_async
            def create_repayment_and_update():
                with transaction.atomic():
                    # Create repayment record
                    repayment = LoanRepayment.objects.create(
                        loan=loan,
                        amount=amount,
                        transaction_reference=transaction_reference
                    )
                    
                    # Calculate total repaid
                    total_repaid = loan.repayments.aggregate(
                        total=models.Sum('amount')
                    )['total'] or 0
                    
                    # Update loan status
                    if total_repaid >= loan.amount_approved:
                        loan.status = 'PAID'
                        status = 'PAID'
                    elif loan.due_date < timezone.now():
                        loan.status = 'OVERDUE'
                        status = 'OVERDUE'
                    else:
                        loan.status = 'ACTIVE'
                        status = 'ACTIVE'
                    
                    loan.save()
                    return repayment, total_repaid, status

            repayment, total_repaid, status = await create_repayment_and_update()
            
            # Send SMS notifications
            try:
                if status == 'PAID':
                    await self.sms_service.send_sms(
                        loan.farmer.phone_number,
                        f"Congratulations! Your loan of {loan.amount_approved} RWF has been fully repaid."
                    )
                else:
                    await self.sms_service.send_sms(
                        loan.farmer.phone_number,
                        f"Payment of {amount} RWF received. Remaining balance: {loan.amount_approved - total_repaid} RWF"
                    )
            except Exception as e:
                print(f"SMS notification failed: {e}")
                # Don't fail the repayment just because SMS failed
            
            return True, "Repayment processed successfully"
            
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_loan_balance(loan):
        """Get current loan balance"""
        total_repaid = loan.repayments.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        return max(loan.amount_approved - total_repaid, 0)


class DynamicCreditScoringService:
    def __init__(self):
        from .external.satellite_api import SatelliteDataService
        from .external.weather_api import WeatherService
        
        self.satellite_service = SatelliteDataService()
        self.weather_service = WeatherService()
        self.sms_service = SMSService()
    
    async def generate_credit_score(self, farmer):
        """Generate a comprehensive credit score based on multiple data sources"""
        # Start with traditional credit score
        traditional_score = await sync_to_async(LoanService.calculate_credit_score)(farmer)
        
        try:
            # Get satellite data about farm health
            satellite_score = await self.satellite_service.analyze_farm(
                farmer.location, 
                farmer.farm_size
            )
            
            # Get mobile money transaction history
            @sync_to_async
            def get_transaction_history():
                # In a real implementation, this would query mobile money API
                # For now, return a mock score based on previous loans
                previous_on_time = Loan.objects.filter(
                    farmer=farmer, 
                    status='PAID',
                    due_date__gte=timezone.now() - timedelta(days=365)
                ).count()
                return min(previous_on_time * 10, 100)
            
            transaction_score = await get_transaction_history()
            
            # Get climate risk assessment for farmer's region
            climate_risk_score = await self.weather_service.assess_risk(farmer.location)
            
            # Calculate weighted score (adjust weights based on importance)
            final_score = (
                traditional_score * 0.4 + 
                satellite_score * 0.2 + 
                transaction_score * 0.3 + 
                climate_risk_score * 0.1
            )
            
            return min(max(final_score, 0), 100)  # Ensure score is between 0-100
            
        except Exception as e:
            print(f"Error in dynamic credit scoring: {e}")
            # Fall back to traditional scoring if dynamic scoring fails
            return traditional_score