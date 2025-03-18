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
    
    REPAYMENT_SCHEDULE_TYPE = [
        ('FIXED', 'Fixed Monthly'),
        ('HARVEST', 'Harvest-Based'),
        ('CUSTOM', 'Custom Schedule'),
    ]
    
    repayment_schedule_type = models.CharField(
        max_length=20, 
        choices=REPAYMENT_SCHEDULE_TYPE,
        default='FIXED'
    )
    
    # For harvest-based loans, how many days after harvest is payment due
    grace_period_days = models.IntegerField(default=30)

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
    loan = models.ForeignKey(
        'Loan',
        on_delete=models.CASCADE,
        related_name='payment_schedules' 
    )
    installment_number = models.IntegerField()
    due_date = models.DateTimeField()
    principal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('PARTIAL', 'Partially Paid'),
            ('PAID', 'Paid'),
            ('OVERDUE', 'Overdue')
        ],
        default='PENDING'
    )
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_reminder_sent = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment Schedule {self.installment_number} for Loan {self.loan.id}"


# Add to loans/models.py

class CropCycle(models.Model):
    """Represents a farmer's crop growing cycle"""
    CROP_TYPE_CHOICES = [
        ('MAIZE', 'Maize'),
        ('BEANS', 'Beans'),
        ('RICE', 'Rice'),
        ('CASSAVA', 'Cassava'),
        ('POTATO', 'Potato'),
        ('COFFEE', 'Coffee'),
        ('TEA', 'Tea'),
        ('OTHER', 'Other'),
    ]
    
    SEASON_CHOICES = [
        ('SEASON_A', 'Season A (Sep-Feb)'),
        ('SEASON_B', 'Season B (Mar-Jun)'),
        ('SEASON_C', 'Season C (Jul-Aug)'),
        ('PERENNIAL', 'Perennial'),
    ]
    
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='crop_cycles')
    crop_type = models.CharField(max_length=20, choices=CROP_TYPE_CHOICES)
    season = models.CharField(max_length=20, choices=SEASON_CHOICES)
    planting_date = models.DateField()
    expected_harvest_date = models.DateField()
    farm_size_allocated = models.DecimalField(max_digits=5, decimal_places=2)  # in hectares
    estimated_yield = models.DecimalField(max_digits=10, decimal_places=2, default=1000.0)
    estimated_revenue = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_harvest_date = models.DateField(null=True, blank=True)
    actual_yield = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-expected_harvest_date']
    
    def __str__(self):
        return f"{self.farmer.name} - {self.get_crop_type_display()} ({self.get_season_display()})"


class HarvestBasedPaymentSchedule(models.Model):
    """Payment schedule aligned with harvest dates"""
    loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name='harvest_schedule')
    crop_cycle = models.ForeignKey(CropCycle, on_delete=models.SET_NULL, null=True, related_name='loan_schedules')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Harvest schedule for loan #{self.loan.id}"


class HarvestPaymentInstallment(models.Model):
    """Individual payment installment in a harvest-based schedule"""
    schedule = models.ForeignKey(HarvestBasedPaymentSchedule, on_delete=models.CASCADE, related_name='installments')
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    percentage_of_harvest = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 30% of harvest
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['due_date']
    
    def __str__(self):
        return f"Payment of {self.amount} due on {self.due_date}"
    
class LoanToken(models.Model):
    """Model for tokenized loans that can only be spent on agricultural inputs"""
    loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name='token')
    token = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVE', 'Active'),
            ('USED', 'Used'),
            ('EXPIRED', 'Expired'),
            ('CANCELLED', 'Cancelled')
        ],
        default='ACTIVE'
    )
    expiry_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Token {self.token} for Loan {self.loan.id}"

class ApprovedVendor(models.Model):
    """Model for approved agricultural input vendors"""
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    location = models.CharField(max_length=100)
    business_type = models.CharField(
        max_length=20,
        choices=[
            ('SEEDS', 'Seeds Supplier'),
            ('FERTILIZER', 'Fertilizer Supplier'),
            ('EQUIPMENT', 'Farm Equipment'),
            ('GENERAL', 'General Agri-Inputs')
        ]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class TokenTransaction(models.Model):
    """Model for token redemption transactions"""
    token = models.ForeignKey(LoanToken, on_delete=models.CASCADE, related_name='transactions')
    vendor = models.ForeignKey(ApprovedVendor, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Transaction {self.reference}"

class HistoricalYield(models.Model):
    """Model to track farmer's historical crop yields"""
    farmer = models.ForeignKey('farmers.Farmer', on_delete=models.CASCADE, related_name='historical_yields')
    crop_type = models.CharField(
        max_length=20,
        choices=[
            ('MAIZE', 'Maize'),
            ('BEANS', 'Beans'),
            ('RICE', 'Rice'),
            ('COFFEE', 'Coffee'),
            ('TEA', 'Tea'),
            ('OTHER', 'Other')
        ]
    )
    season = models.CharField(max_length=20)
    year = models.IntegerField()
    yield_amount = models.DecimalField(max_digits=10, decimal_places=2)  # In kg
    farm_size_used = models.DecimalField(max_digits=5, decimal_places=2)  # In hectares
    
    def __str__(self):
        return f"{self.farmer.name} - {self.get_crop_type_display()} ({self.year})"