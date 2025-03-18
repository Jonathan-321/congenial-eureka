from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from farmers.models import Farmer
from authentication.models import User
from ..models import LoanProduct, Loan

class LoanAPITests(TestCase):
    def setUp(self):
        # Create test user and farmer
        self.user = User.objects.create_user(
            username='testfarmer',
            password='test123',
            phone_number='+250789123456'
        )
        self.farmer = Farmer.objects.create(
            user=self.user,
            name='Test Farmer',
            phone_number='+250789123456',
            location='Test Location',
            farm_size=2.5
        )
        
        # Create test loan product
        self.loan_product = LoanProduct.objects.create(
            name='Test Product',
            description='Test loan product',
            min_amount=Decimal('100.00'),
            max_amount=Decimal('1000.00'),
            interest_rate=Decimal('10.00'),
            duration_days=30,
            is_active=True,
            requirements={'credit_score': 700}
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_loan_application_success(self):
        """Test successful loan application"""
        url = reverse('loan-apply', kwargs={'pk': self.loan_product.id})  # Corrected URL
        data = {
            'loan_product': self.loan_product.id,
            'amount': '500.00'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Changed to 200
        self.assertEqual(response.data['status'], 'PENDING')
        self.assertIn('loan_id', response.data)

    def test_loan_application_invalid_amount(self):
        """Test loan application with invalid amount"""
        url = reverse('loan-apply', kwargs={'pk': self.loan_product.id})  # Corrected URL
        data = {
            'loan_product': self.loan_product.id,
            'amount': '2000.00'  # Above max_amount
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_loan_approval_success(self):
        """Test successful loan approval"""
        loan = Loan.objects.create(
            farmer=self.farmer,
            loan_product=self.loan_product,
            amount_requested=Decimal('500.00'),
            status='PENDING'
        )
        url = reverse('loan-approve', kwargs={'pk': loan.id})
        data = {'amount': '500.00'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'APPROVED')

    def test_loan_disbursement_success(self):
        """Test successful loan disbursement"""
        loan = Loan.objects.create(
            farmer=self.farmer,
            loan_product=self.loan_product,
            amount_requested=Decimal('500.00'),
            amount_approved=Decimal('500.00'),
            status='APPROVED'
        )
        url = reverse('loan-disburse', kwargs={'pk': loan.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'DISBURSED')