from django.contrib import admin
from .models import Loan, LoanProduct, LoanRepayment, Transaction

@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_amount', 'max_amount', 'interest_rate', 'duration_days', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)
    ordering = ('name',)

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'farmer', 
        'loan_product',
        'amount_requested', 
        'amount_approved',
        'status', 
        'application_date'
    )
    list_filter = ('status',)
    search_fields = ('farmer__name', 'farmer__phone_number', 'id')
    readonly_fields = ('application_date', 'momo_reference')

@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ('loan', 'amount', 'payment_date', 'transaction_reference')
    search_fields = ('loan__farmer__name', 'transaction_reference')
    readonly_fields = ('payment_date',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'loan', 'transaction_type', 'amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status')
    search_fields = ('reference', 'loan__farmer__name')
    readonly_fields = ('created_at', 'updated_at')