from decimal import Decimal
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import sync_to_async
from .models import Loan, LoanRepayment, PaymentSchedule

class LoanAnalyticsService:
    @staticmethod
    @sync_to_async
    def get_portfolio_summary():
        """Get summary of loan portfolio"""
        current_date = timezone.now()
        
        # Active loans summary
        active_loans = Loan.objects.filter(status__in=['ACTIVE', 'OVERDUE'])
        
        # Calculate total disbursed amount
        total_disbursed = active_loans.aggregate(
            total=Sum('amount_approved')
        )['total'] or 0
        
        # Calculate total outstanding amount
        total_repaid = LoanRepayment.objects.filter(
            loan__in=active_loans,
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_outstanding = total_disbursed - total_repaid
        
        # Calculate default rate (loans overdue by more than 30 days)
        overdue_30_days = active_loans.filter(
            status='OVERDUE',
            schedules__due_date__lt=current_date - timedelta(days=30),
            schedules__status='PENDING'
        ).distinct().count()
        
        total_active = active_loans.count()
        default_rate = (overdue_30_days / total_active) * 100 if total_active > 0 else 0
        
        return {
            'total_active_loans': total_active,
            'total_disbursed': total_disbursed,
            'total_outstanding': total_outstanding,
            'default_rate': default_rate,
            'at_risk_amount': active_loans.filter(status='OVERDUE').aggregate(
                total=Sum('amount_approved'))['total'] or 0,
        }
    
    @staticmethod
    @sync_to_async
    def get_farmer_performance(farmer_id):
        """Get performance metrics for a specific farmer"""
        # Get all loans for this farmer
        loans = Loan.objects.filter(farmer_id=farmer_id)
        
        # Get completed loans
        completed_loans = loans.filter(status='PAID')
        
        # Calculate on-time payment rate
        total_schedules = PaymentSchedule.objects.filter(loan__in=loans).count()
        late_payments = PaymentSchedule.objects.filter(
            loan__in=loans,
            status='PAID',
            payment_date__gt=F('due_date')
        ).count()
        
        on_time_rate = ((total_schedules - late_payments) / total_schedules * 100) if total_schedules > 0 else 0
        
        # Calculate average days to repay
        avg_days = completed_loans.annotate(
            days_to_repay=F('completion_date') - F('disbursement_date')
        ).aggregate(avg=Avg('days_to_repay'))['avg']
        
        avg_days_to_repay = avg_days.days if avg_days else 0
        
        return {
            'total_loans': loans.count(),
            'completed_loans': completed_loans.count(),
            'active_loans': loans.filter(status__in=['ACTIVE', 'OVERDUE']).count(),
            'on_time_payment_rate': on_time_rate,
            'avg_days_to_repay': avg_days_to_repay,
            'total_borrowed': loans.aggregate(total=Sum('amount_approved'))['total'] or 0,
            'credit_score': loans.latest('created_at').credit_score if loans.exists() else 0,
        }
    
    @staticmethod
    @sync_to_async
    def get_default_risk_factors():
        """Analyze factors correlated with loan defaults"""
        # Get overdue loans
        overdue_loans = Loan.objects.filter(status='OVERDUE')
        
        # Get paid loans
        paid_loans = Loan.objects.filter(status='PAID')
        
        if not overdue_loans.exists() or not paid_loans.exists():
            return {"message": "Insufficient data for analysis"}
        
        # Analyze by location
        location_default = {}
        for loan in overdue_loans:
            location = loan.farmer.location
            location_default[location] = location_default.get(location, 0) + 1
        
        # Analyze by loan amount
        avg_overdue_amount = overdue_loans.aggregate(avg=Avg('amount_approved'))['avg'] or 0
        avg_paid_amount = paid_loans.aggregate(avg=Avg('amount_approved'))['avg'] or 0
        
        # Analyze by crop type (if available)
        crop_default = {}
        for loan in overdue_loans:
            crop_cycles = loan.farmer.cropcycle_set.all()
            for cycle in crop_cycles:
                crop = cycle.crop_type
                crop_default[crop] = crop_default.get(crop, 0) + 1
        
        return {
            'high_risk_locations': sorted(location_default.items(), key=lambda x: x[1], reverse=True),
            'avg_overdue_amount': avg_overdue_amount,
            'avg_paid_amount': avg_paid_amount,
            'high_risk_crops': sorted(crop_default.items(), key=lambda x: x[1], reverse=True) if crop_default else [],
        }