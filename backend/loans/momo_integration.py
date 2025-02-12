import httpx
import base64
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from .models import Transaction, Loan
from asgiref.sync import sync_to_async
from decimal import Decimal


class MoMoAPI:
    def __init__(self):
        self.base_url = settings.MOMO_API_URL
        self.subscription_key = settings.MOMO_SUBSCRIPTION_KEY
        self.collection_key = settings.MOMO_COLLECTION_KEY
        self.api_user = settings.MOMO_API_USER
        self.api_key = settings.MOMO_API_KEY
        self.token = None

    async def get_access_token(self, is_collection=False):
        """Get OAuth 2.0 access token"""
        auth_string = f"{self.api_user}:{self.api_key}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Ocp-Apim-Subscription-Key": self.collection_key if is_collection else self.subscription_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Target-Environment": settings.MOMO_ENVIRONMENT
        }
        
        endpoint = "collection/token/" if is_collection else "disbursement/token/"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/{endpoint}",
                headers=headers,
                data=""
            )
            if response.status_code == 200:
                self.token = response.json().get('access_token')
                return self.token
            raise Exception(f"Failed to get token: {response.text}")

    async def initiate_disbursement(self, loan_id, amount, phone_number):
        """
        Initiate a loan disbursement to farmer's mobile money account
        Args:
            loan_id: ID of the loan being disbursed
            amount: Amount to disburse
            phone_number: Recipient's phone number
        """
        # Get the loan instance
        try:
            loan = Loan.objects.get(id=loan_id)
        except Loan.DoesNotExist:
            raise Exception("Loan not found")

        # Generate unique reference
        reference = str(uuid.uuid4())

        # Create transaction record
        transaction = Transaction.objects.create(
            loan=loan,
            transaction_type='DISBURSEMENT',
            amount=amount,
            currency='EUR',
            reference=reference,
            phone_number=phone_number,
            status='PENDING'
        )

        # Get access token if not available
        if not self.token:
            await self.get_access_token()

        # Format phone number (remove + if present)
        formatted_phone = phone_number.replace('+', '')

        headers = {
            'Authorization': f'Bearer {self.token}',
            'X-Reference-Id': reference,
            'X-Target-Environment': settings.MOMO_ENVIRONMENT,
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'amount': str(amount),
            'currency': 'EUR',
            'externalId': reference,
            'payee': {
                'partyIdType': 'MSISDN',
                'partyId': formatted_phone
            },
            'payerMessage': 'Loan Disbursement',
            'payeeNote': 'Farm Loan'
        }

        print("\nSending disbursement request:")
        print(f"URL: {self.base_url}/disbursement/v1_0/transfer")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f'{self.base_url}/disbursement/v1_0/transfer',
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                print(f"\nResponse received:")
                print(f"Status Code: {response.status_code}")
                print(f"Headers: {response.headers}")
                print(f"Body: {response.text}")
                
                if response.status_code in [201, 202]:
                    # Update loan status
                    loan.disbursement_status = 'PROCESSING'
                    loan.momo_reference = reference
                    loan.save()
                    
                    return {
                        'status': 'pending',
                        'reference': reference,
                        'message': 'Disbursement initiated successfully'
                    }
                else:
                    # Update transaction status to failed
                    transaction.status = 'FAILED'
                    transaction.save()
                    raise Exception(f"Disbursement failed: {response.text}")
                    
            except httpx.RequestError as e:
                # Update transaction status on network error
                transaction.status = 'FAILED'
                transaction.save()
                raise Exception(f"Network error: {str(e)}")

    async def check_disbursement_status(self, reference):
        """
        Check the status of a disbursement
        Args:
            reference: Transaction reference ID
        """
        if not self.token:
            await self.get_access_token()

        headers = {
            'Authorization': f'Bearer {self.token}',
            'X-Target-Environment': settings.MOMO_ENVIRONMENT,
            'Ocp-Apim-Subscription-Key': self.subscription_key
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.base_url}/disbursement/v1_0/transfer/{reference}',
                headers=headers
            )
            
            if response.status_code == 200:
                status_data = response.json()
                
                # Update transaction status
                try:
                    transaction = Transaction.objects.get(reference=reference)
                    transaction.status = 'SUCCESSFUL' if status_data.get('status') == 'SUCCESSFUL' else 'FAILED'
                    transaction.save()
                    
                    # Update loan status if transaction is successful
                    if transaction.status == 'SUCCESSFUL':
                        loan = transaction.loan
                        loan.disbursement_status = 'COMPLETED'
                        loan.disbursement_date = timezone.now()
                        loan.status = 'ACTIVE'
                        loan.save()
                except Transaction.DoesNotExist:
                    pass
                
                return status_data
            else:
                raise Exception(f"Failed to check disbursement status: {response.text}")

    async def request_payment(self, loan_id, amount, phone_number):
        """
        Request a loan repayment from farmer's mobile money account
        Args:
            loan_id: ID of the loan being repaid
            amount: Amount to collect
            phone_number: Payer's phone number
        """
         # Get the loan instance
        try:
            loan = await sync_to_async(Loan.objects.get)(id=loan_id)
        except Loan.DoesNotExist:
            raise Exception("Loan not found")

        # Generate unique reference
        reference = str(uuid.uuid4())

        # Create transaction record
        transaction = await sync_to_async(Transaction.objects.create)(
            loan=loan,
            transaction_type='REPAYMENT',
            amount=amount,
            currency='EUR',
            reference=reference,
            phone_number=phone_number,
            status='PENDING'
        )

        # Get collection token
        await self.get_access_token(is_collection=True)

        # Format phone number
        formatted_phone = phone_number.replace('+', '')

        headers = {
            'Authorization': f'Bearer {self.token}',
            'X-Reference-Id': reference,
            'X-Target-Environment': settings.MOMO_ENVIRONMENT,
            'Ocp-Apim-Subscription-Key': self.collection_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'amount': str(amount),
            'currency': 'EUR',
            'externalId': reference,
            'payer': {
                'partyIdType': 'MSISDN',
                'partyId': formatted_phone
            },
            'payerMessage': 'Loan Repayment',
            'payeeNote': 'Farm Loan Repayment'
        }

        print("\nSending payment request:")
        print(f"URL: {self.base_url}/collection/v1_0/requesttopay")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f'{self.base_url}/collection/v1_0/requesttopay',
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                print(f"\nResponse received:")
                print(f"Status Code: {response.status_code}")
                print(f"Headers: {response.headers}")
                print(f"Body: {response.text}")
                
                if response.status_code == 202:
                    return {
                        'status': 'pending',
                        'reference': reference,
                        'message': 'Payment request initiated successfully'
                    }
                else:
                    # Update transaction status
                    transaction.status = 'FAILED'
                    transaction.save()
                    raise Exception(f"Payment request failed: {response.text}")
                    
            except httpx.RequestError as e:
                # Update transaction status on network error
                transaction.status = 'FAILED'
                transaction.save()
                raise Exception(f"Network error: {str(e)}")

    async def check_payment_status(self, reference):
        """Check the status of a payment request"""
        if not self.token:
            await self.get_access_token(is_collection=True)

        headers = {
            'Authorization': f'Bearer {self.token}',
            'X-Target-Environment': settings.MOMO_ENVIRONMENT,
            'Ocp-Apim-Subscription-Key': self.collection_key
        }
        
        print("\nSending status check request:")
        print(f"URL: {self.base_url}/collection/v1_0/requesttopay/{reference}")
        print(f"Headers: {headers}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.base_url}/collection/v1_0/requesttopay/{reference}',
                headers=headers
            )
            
            print(f"\nResponse received:")
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {response.headers}")
            print(f"Body: {response.text}")
            
            if response.status_code == 200:
                status_data = response.json()
                
                # Define all database operations
                get_transaction = sync_to_async(Transaction.objects.get)
                save_transaction = sync_to_async(lambda x: x.save())
                get_loan = sync_to_async(lambda x: x.loan)
                create_repayment = sync_to_async(lambda l, **kwargs: l.repayments.create(**kwargs))
                get_total_repaid = sync_to_async(lambda l: l.repayments.aggregate(models.Sum('amount')))
                
                try:
                    # Get transaction
                    transaction = await get_transaction(reference=reference)
                    transaction.status = 'SUCCESSFUL' if status_data.get('status') == 'SUCCESSFUL' else 'FAILED'
                    await save_transaction(transaction)
                    
                    if transaction.status == 'SUCCESSFUL':
                        # Get loan using async operation
                        loan = await get_loan(transaction)
                        
                        # Create repayment record
                        await create_repayment(
                            loan,
                            amount=transaction.amount,
                            transaction_reference=reference
                        )
                        
                        # Get total repaid amount
                        total_repaid = await get_total_repaid(loan)
                        total_repaid_amount = total_repaid['amount__sum'] or 0
                        
                        print(f"\nLoan details:")
                        print(f"Amount approved: {loan.amount_approved} EUR")
                        print(f"Total repaid: {total_repaid_amount} EUR")
                        
                        # Update loan status if fully paid
                        if Decimal(str(total_repaid_amount)) >= loan.amount_approved:
                            print("Loan fully paid, updating status...")
                            loan.status = 'PAID'
                            await save_transaction(loan)
                            print(f"Loan status updated to: {loan.status}")
                        
                    print(f"\nTransaction status updated: {transaction.status}")
                    if transaction.status == 'SUCCESSFUL':
                        print(f"Repayment recorded: {transaction.amount} EUR")
                    
                except Transaction.DoesNotExist:
                    print(f"Transaction with reference {reference} not found")