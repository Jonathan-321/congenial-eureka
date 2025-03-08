from decimal import Decimal
from datetime import datetime, timedelta
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
import httpx
import uuid
from .models import Loan, LoanRepayment, PaymentSchedule, LoanProduct
from .momo_integration import MoMoAPI
from .sms_service import SMSService 
from asgiref.sync import sync_to_async

class SMSService:
    @staticmethod
    async def send_sms(phone_number, message):
        """Send SMS using Africa's Talking API"""
        try:
            url = "https://api.africastalking.com/version1/messaging"
            headers = {
                'ApiKey': settings.AT_API_KEY,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            data = {
                'username': settings.AT_USERNAME,
                'to': phone_number,
                'message': message
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, data=data)
                return True, response.json()
        except Exception as e:
            return False, str(e)



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



    async def apply_for_loan(self, farmer, loan_product_id: uuid.UUID, amount: Decimal) -> dict:
        try:
            async with transaction.atomic():
                product = await LoanProduct.objects.aget(id=loan_product_id)
                eligibility = await self._check_eligibility(farmer, product, amount)
                
                if not eligibility['eligible']:
                    return {'status': 'REJECTED', 'message': eligibility['reason']}

                loan = await Loan.objects.acreate(
                    farmer=farmer,
                    loan_product=product,
                    amount_requested=amount,
                    status='PENDING'
                )

                # Send SMS notification
                await self.sms_service.send_sms(
                    farmer.phone_number,
                    f"Your loan application for {amount} RWF is being processed."
                )

                return {'status': 'PENDING', 'loan_id': loan.id}

        except Exception as e:
            return {'status': 'ERROR', 'message': str(e)}

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
            return False, "Requested amount outside product limits"
            
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
            # Check eligibility
            eligible, message = LoanService.check_loan_eligibility(farmer, loan_product, amount)
            if not eligible:
                return False, message
                
            # Calculate credit score
            credit_score = LoanService.calculate_credit_score(farmer)
            
            # Create loan record
            loan = Loan.objects.create(
                farmer=farmer,
                loan_product=loan_product,
                amount_requested=amount,
                amount_approved=amount,
                credit_score=credit_score,
                status='APPROVED',
                due_date=datetime.now() + timedelta(days=loan_product.term_days)
            )
            
            # Send approval SMS
            await SMSService.send_sms(
                farmer.phone_number,
                f"Your loan of {amount} RWF has been approved. Disbursement in progress."
            )
            
            # Initiate disbursement
            success, result = await LoanService.initiate_loan_disbursement(loan)
            
            return success, result
            
        except Exception as e:
            return False, str(e)

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

class LoanRepaymentService:
    @staticmethod
    async def process_repayment(loan, amount, transaction_reference):
        """Process a loan repayment"""
        try:
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
                # Send completion SMS
                await SMSService.send_sms(
                    loan.farmer.phone_number,
                    f"Congratulations! Your loan of {loan.amount_approved} RWF has been fully repaid."
                )
            elif loan.due_date < datetime.now():
                loan.status = 'OVERDUE'
            else:
                loan.status = 'ACTIVE'
                # Send confirmation SMS
                await SMSService.send_sms(
                    loan.farmer.phone_number,
                    f"Payment of {amount} RWF received. Remaining balance: {loan.amount_approved - total_repaid} RWF"
                )
                
            loan.save()
            
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


