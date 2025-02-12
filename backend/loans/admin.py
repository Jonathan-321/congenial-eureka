from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Loan, LoanProduct, LoanRepayment

@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_amount', 'max_amount', 'interest_rate', 'term_days', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('id', 'farmer', 'amount_requested', 'status', 'application_date', 'due_date')
    list_filter = ('status', 'disbursement_status')
    search_fields = ('farmer__name', 'farmer__phone_number')
    readonly_fields = ('application_date',)

@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ('loan', 'amount', 'payment_date', 'transaction_reference')
    search_fields = ('loan__farmer__name', 'transaction_reference')