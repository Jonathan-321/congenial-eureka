from rest_framework import serializers
from .models import Loan, LoanProduct, LoanRepayment, Transaction
from .models import PaymentSchedule


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
            from django.utils import timezone
            return (timezone.now() - obj.due_date).days
        return 0
        
    def get_total_due(self, obj):
        return obj.amount + obj.penalty_amount - obj.amount_paid
    
class LoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanProduct
        fields = [
            'id', 'name', 'description',
            'min_amount', 'max_amount',
            'interest_rate', 'duration_days',
            'is_active', 'requirements'
        ]

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
        fields = ['id', 'loan', 'amount', 'payment_date', 'transaction_reference']
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