from decimal import Decimal
from datetime import datetime, timedelta
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
import httpx
import uuid
from .models import Loan, LoanRepayment, PaymentSchedule, LoanProduct
from .momo_integration import MoMoAPI
from .sms_service import SMSService  # Now this import will work

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


class LoanService:
    def __init__(self):
        self.momo_api = MoMoAPI()
        self.sms_service = SMSService()

    async def create_payment_schedule(self, loan: Loan) -> None:
        """Create payment schedule for a loan"""
        amount_per_payment = loan.amount_approved / loan.loan_product.term_months
        interest_rate = loan.loan_product.interest_rate / 12  # Monthly interest
        
        current_date = loan.disbursement_date
        remaining_balance = loan.amount_approved
        
        schedules = []
        for month in range(loan.loan_product.term_months):
            interest_amount = remaining_balance * interest_rate
            total_payment = amount_per_payment + interest_amount
            
            due_date = current_date + timedelta(days=30)
            
            schedules.append(PaymentSchedule(
                loan=loan,
                due_date=due_date,
                principal_amount=amount_per_payment,
                interest_amount=interest_amount,
                total_amount=total_payment,
                status='PENDING'
            ))
            
            remaining_balance -= amount_per_payment
            current_date = due_date
            
        await PaymentSchedule.objects.abulk_create(schedules)

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

                # Update loan status
                total_repaid = await self.get_loan_balance(loan)
                
                if total_repaid >= loan.amount_approved:
                    loan.status = 'PAID'
                elif loan.due_date < timezone.now():
                    loan.status = 'OVERDUE'
                else:
                    loan.status = 'ACTIVE'
                
                await loan.asave()

                # Send SMS confirmation
                await self.sms_service.send_sms(
                    loan.farmer.phone_number,
                    f"Payment of {amount} RWF received. Remaining balance: {loan.amount_approved - total_repaid} RWF"
                )

                return {'status': 'SUCCESS', 'message': 'Repayment processed'}

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