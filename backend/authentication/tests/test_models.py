import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse
from loans.models import Loan, LoanProduct
from farmers.models import Farmer

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def create_user():
    def make_user(**kwargs):
        return User.objects.create_user(**kwargs)
    return make_user

@pytest.fixture
def create_farmer():
    def make_farmer(user, **kwargs):
        return Farmer.objects.create(user=user, **kwargs)
    return make_farmer

@pytest.fixture
def create_loan_product():
    def make_loan_product(**kwargs):
        return LoanProduct.objects.create(**kwargs)
    return make_loan_product

@pytest.fixture
def create_loan():
    def make_loan(farmer, loan_product, **kwargs):
        return Loan.objects.create(farmer=farmer, loan_product=loan_product, **kwargs)
    return make_loan

@pytest.mark.django_db
async def test_apply_for_loan(api_client, create_user, create_farmer, create_loan_product):
    user = create_user(username='testuser', password='testpassword', role='FARMER', phone_number='+250789123456')
    farmer = create_farmer(user=user, name='Test Farmer', location='Kigali', farm_size=1.5)
    loan_product = create_loan_product(name='AgriLoan', description='Loan for farmers', min_amount=100, max_amount=1000, interest_rate=5.0, duration_days=30)

    api_client.force_authenticate(user=user)
    url = reverse('loan-list')
    data = {'loan_product': loan_product.id, 'amount_requested': 500}
    response = await api_client.post(url, data, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    assert Loan.objects.count() == 1

@pytest.mark.django_db
async def test_approve_loan(api_client, create_user, create_farmer, create_loan_product, create_loan):
    user = create_user(username='testuser', password='testpassword', role='ADMIN', phone_number='+250789123456')
    farmer_user = create_user(username='farmeruser', password='testpassword', role='FARMER', phone_number='+250789123457')
    farmer = create_farmer(user=farmer_user, name='Test Farmer', location='Kigali', farm_size=1.5)
    loan_product = create_loan_product(name='AgriLoan', description='Loan for farmers', min_amount=100, max_amount=1000, interest_rate=5.0, duration_days=30)
    loan = create_loan(farmer=farmer, loan_product=loan_product, amount_requested=500)

    api_client.force_authenticate(user=user)
    url = reverse('loan-approve', kwargs={'pk': loan.id})  # Assuming you have a named URL for approve
    response = await api_client.post(url, {'amount': 500}, format='json')

    assert response.status_code == status.HTTP_200_OK
    loan.refresh_from_db()
    assert loan.status == 'APPROVED'

@pytest.mark.django_db
async def test_disburse_loan(api_client, create_user, create_farmer, create_loan_product, create_loan):
    user = create_user(username='testuser', password='testpassword', role='ADMIN', phone_number='+250789123456')
    farmer_user = create_user(username='farmeruser', password='testpassword', role='FARMER', phone_number='+250789123457')
    farmer = create_farmer(user=farmer_user, name='Test Farmer', location='Kigali', farm_size=1.5)
    loan_product = create_loan_product(name='AgriLoan', description='Loan for farmers', min_amount=100, max_amount=1000, interest_rate=5.0, duration_days=30)
    loan = create_loan(farmer=farmer, loan_product=loan_product, amount_requested=500, amount_approved=500, status='APPROVED')

    api_client.force_authenticate(user=user)
    url = reverse('loan-disburse', kwargs={'pk': loan.id})  # Assuming you have a named URL for disburse
    response = await api_client.post(url, format='json')

    assert response.status_code == status.HTTP_200_OK
    loan.refresh_from_db()
    assert loan.status == 'DISBURSED'