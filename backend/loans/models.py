from django.db import models
from authentication.models import User
from farmers.models import Farmer
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

class LoanProduct(models.Model):
    """Predefined loan products with specific terms"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    min_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    max_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2
    )
    interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        help_text="Annual interest rate as a percentage"
    )
    duration_days = models.IntegerField(
        help_text="Loan duration in days"
    )
    is_active = models.BooleanField(default=True)
    requirements = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.interest_rate}% APR)"

class Loan(models.Model):
    """Represents a loan issued to a farmer."""

    LOAN_STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('DISBURSED', 'Disbursed'),
        ('ACTIVE', 'Active'),
        ('OVERDUE', 'Overdue'),
        ('PAID', 'Paid'),
        ('DEFAULTED', 'Defaulted'),
        ('REJECTED', 'Rejected'),
    ]

    DISBURSEMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(
        Farmer, 
        on_delete=models.PROTECT,
        related_name='loans'
    )
    loan_product = models.ForeignKey(
        LoanProduct,
        on_delete=models.PROTECT
    )
    amount_requested = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    amount_approved = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=LOAN_STATUS_CHOICES,
        default='PENDING'
    )
    disbursement_status = models.CharField(
        max_length=20,
        choices=DISBURSEMENT_STATUS,
        default='PENDING'
    )
    application_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    disbursement_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    credit_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    momo_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-application_date']

    def __str__(self):
        return f"Loan #{self.id} - {self.farmer.name} - {self.status}"

class LoanRepayment(models.Model):
    """Track individual repayment transactions"""
    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name='repayments'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_reference = models.CharField(max_length=100)
    
    def __str__(self):
        return f"Repayment of {self.amount} for Loan #{self.loan.id}"
    

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('DISBURSEMENT', 'Loan Disbursement'),
        ('REPAYMENT', 'Loan Repayment'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESSFUL', 'Successful'),
        ('FAILED', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan = models.ForeignKey(
        'loans.Loan', 
        on_delete=models.CASCADE, 
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=20, 
        choices=TRANSACTION_TYPES,
        db_index=True  # Add index for faster queries
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')
    reference = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=15)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING',
        db_index=True  # Add index for faster queries
    )
    financial_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_type', 'status'])
        ]
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} {self.currency} - {self.status}"



class PaymentSchedule(models.Model):
    loan = models.ForeignKey('Loan', on_delete=models.CASCADE, related_name='payment_schedule')
    installment_number = models.IntegerField()
    due_date = models.DateTimeField()
    principal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('PAID', 'Paid'),
            ('OVERDUE', 'Overdue'),
            ('PARTIALLY_PAID', 'Partially Paid')
        ],
        default='PENDING'
    )
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    last_reminder_sent = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date']