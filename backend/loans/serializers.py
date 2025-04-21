# backend/loans/serializers.py
from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal

from farmers.models import Farmer
from farmers.serializers import SimpleFarmerSerializer
from .models import (
    Loan, LoanProduct, LoanRepayment, Transaction, PaymentSchedule,
    LoanToken, TokenTransaction, ApprovedVendor,
    CropCycle, HarvestBasedPaymentSchedule, HarvestPaymentInstallment
)
from rest_framework import serializers
from .models import Farmer


# Base serializers
class LoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanProduct
        fields = ['id', 'name', 'description', 'min_amount', 'max_amount', 
                 'interest_rate', 'duration_days', 'repayment_schedule_type', 
                 'is_active']
class SimpleLoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = ['id', 'amount_approved', 'status', 'disbursement_status', 
                 'application_date', 'due_date']

class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = [
            'id', 'farmer', 'loan_product', 
            'amount_requested', 'amount_approved',
            'status', 'application_date',
            'approval_date', 'disbursement_date',
            'due_date', 'credit_score'
        ]
        read_only_fields = [
            'status', 'approval_date', 
            'disbursement_date', 'due_date'
        ]

class LoanRepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRepayment
        fields = ['id', 'loan', 'amount', 'payment_date', 'payment_method', 'reference']
        read_only_fields = ['payment_date']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id', 'loan', 'transaction_type',
            'amount', 'currency', 'status',
            'reference', 'created_at'
        ]
        read_only_fields = ['created_at']

class PaymentScheduleSerializer(serializers.ModelSerializer):
    loan_id = serializers.UUIDField(source='loan.id', read_only=True)
    days_overdue = serializers.SerializerMethodField()
    total_due = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentSchedule
        fields = [
            'id', 'loan_id', 'installment_number', 'due_date', 
            'amount', 'status', 'amount_paid', 'penalty_amount',
            'days_overdue', 'total_due'
        ]
        
    def get_days_overdue(self, obj):
        if obj.status == 'OVERDUE' and obj.due_date:
            return (timezone.now().date() - obj.due_date).days
        return 0
        
    def get_total_due(self, obj):
        return obj.amount + obj.penalty_amount - obj.amount_paid

# Tokenization serializers
class LoanTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanToken
        fields = ['id', 'token', 'amount', 'status', 'expiry_date', 'created_at']

class TokenTransactionSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    
    class Meta:
        model = TokenTransaction
        fields = ['id', 'amount', 'reference', 'created_at', 'vendor_name']

# Crop cycle and harvest-based payment serializers
class CropCycleSerializer(serializers.ModelSerializer):
    crop_type_display = serializers.CharField(source='get_crop_type_display', read_only=True)
    season_display = serializers.CharField(source='get_season_display', read_only=True)
    
    class Meta:
        model = CropCycle
        fields = ['id', 'crop_type', 'crop_type_display', 'season', 'season_display',
                 'planting_date', 'expected_harvest_date', 'farm_size_allocated',
                 'estimated_yield', 'estimated_revenue', 'notes']

class HarvestPaymentInstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HarvestPaymentInstallment
        fields = ['id', 'due_date', 'amount', 'percentage_of_harvest', 'is_paid', 'payment_date']

class HarvestScheduleSerializer(serializers.ModelSerializer):
    installments = HarvestPaymentInstallmentSerializer(many=True, read_only=True)
    crop_details = CropCycleSerializer(source='crop_cycle', read_only=True)
    
    class Meta:
        model = HarvestBasedPaymentSchedule
        fields = ['id', 'created_at', 'updated_at', 'crop_details', 'installments']

# Composite serializers
class DetailedLoanSerializer(serializers.ModelSerializer):
    farmer = SimpleFarmerSerializer(read_only=True)
    loan_product = LoanProductSerializer(read_only=True)
    repayments = LoanRepaymentSerializer(many=True, read_only=True, source='loanrepayment_set')
    payment_schedule = PaymentScheduleSerializer(read_only=True)
    harvest_schedule = HarvestScheduleSerializer(read_only=True)
    token = LoanTokenSerializer(read_only=True)
    
    class Meta:
        model = Loan
        fields = ['id', 'farmer', 'loan_product', 'amount_requested', 'amount_approved',
                 'status', 'disbursement_status', 'application_date', 'approval_date',
                 'disbursement_date', 'due_date', 'credit_score', 'momo_reference',
                 'repayments', 'payment_schedule', 'harvest_schedule', 'token']

class FarmerDashboardSerializer(serializers.ModelSerializer):
    active_loans_count = serializers.IntegerField(read_only=True)
    total_loan_balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    next_payment_date = serializers.DateField(read_only=True)
    next_payment_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    active_tokens = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Farmer
        fields = ['id', 'name', 'location', 'farm_size', 'active_loans_count', 
                 'total_loan_balance', 'next_payment_date', 'next_payment_amount', 
                 'active_tokens']
        
class FarmerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farmer
        fields = ['id', 'name', 'phone_number', 'location', 'farm_size', 'created_at']


class SimpleFarmerSerializer(serializers.ModelSerializer):
    """A simplified serializer for Farmer model with fewer fields"""
    class Meta:
        model = Farmer
        fields = ['id', 'name', 'location', 'phone_number']

class FarmerDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed farmer information including climate data"""
    climate_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Farmer
        fields = ['id', 'name', 'phone_number', 'location', 'farm_size', 
                 'latitude', 'longitude', 'climate_status', 'created_at']
        
    def get_climate_status(self, obj):
        """Get climate-related statistics for the farmer"""
        status = {
            'has_climate_data': obj.last_climate_update is not None,
            'ndvi_value': obj.ndvi_value,
            'ndvi_status': self._get_ndvi_status(obj.ndvi_value),
            'rainfall_anomaly_mm': obj.rainfall_anomaly_mm,
            'rainfall_status': self._get_rainfall_status(obj.rainfall_anomaly_mm),
            'last_update': obj.last_climate_update
        }
        return status
        
    def _get_ndvi_status(self, ndvi):
        """Convert NDVI value to a descriptive status"""
        if ndvi is None:
            return "Unknown"
        elif ndvi < 0:
            return "Poor vegetation"
        elif ndvi < 0.2:
            return "Sparse vegetation"
        elif ndvi < 0.4:
            return "Moderate vegetation"
        elif ndvi < 0.6:
            return "Good vegetation"
        else:
            return "Dense vegetation"
            
    def _get_rainfall_status(self, anomaly):
        """Convert rainfall anomaly to a descriptive status"""
        if anomaly is None:
            return "Unknown"
        elif anomaly < -30:
            return "Severe drought"
        elif anomaly < -15:
            return "Moderate drought"
        elif anomaly < -5:
            return "Slight drought"
        elif anomaly <= 5:
            return "Normal rainfall"
        elif anomaly <= 15:
            return "Above average rainfall"
        elif anomaly <= 30:
            return "High rainfall"
        else:
            return "Excessive rainfall"

# Update the LoanApplicationSerializer or similar to include our climate data
class LoanApplicationDetailSerializer(serializers.ModelSerializer):
    farmer = FarmerDetailSerializer(read_only=True)
    # ... existing fields ...
    
    class Meta:
        model = Loan
        fields = [
            'id', 'farmer', 'amount', 'purpose', 'status', 'application_date',
            # ... other existing fields ...
        ]


