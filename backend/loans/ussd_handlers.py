from .models import Loan, LoanProduct
from .services import LoanService, LoanRepaymentService
from decimal import Decimal

class LoanUSSDHandler:
    @staticmethod
    def handle_loan_menu(session):
        """Handle main loan menu"""
        if session.level == 1:
            response = """
                Select an option:
                1. Apply for loan
                2. Check loan status
                3. Make repayment
                4. Check loan balance
            """
            session.level = 2
            return response
            
        elif session.level == 2:
            if session.user_input == "1":
                return LoanUSSDHandler.show_loan_products(session)
            elif session.user_input == "2":
                return LoanUSSDHandler.check_loan_status(session)
            elif session.user_input == "3":
                return LoanUSSDHandler.initiate_repayment(session)
            elif session.user_input == "4":
                return LoanUSSDHandler.check_loan_balance(session)

    @staticmethod
    def show_loan_products(session):
        """Show available loan products"""
        products = LoanProduct.objects.filter(is_active=True)
        response = "Select loan product:\n"
        for idx, product in enumerate(products, 1):
            response += f"{idx}. {product.name} ({product.min_amount}-{product.max_amount} RWF)\n"
        
        session.level = 3
        session.context['products'] = list(products)
        return response

    @staticmethod
    def process_loan_application(session):
        """Process loan application"""
        if 'selected_product' not in session.context:
            product_idx = int(session.user_input) - 1
            session.context['selected_product'] = session.context['products'][product_idx]
            return "Enter loan amount:"
            
        amount = Decimal(session.user_input)
        product = session.context['selected_product']
        
        # Check eligibility
        eligible, message = LoanService.check_loan_eligibility(
            session.farmer,
            product,
            amount
        )
        
        if not eligible:
            return f"Loan application failed: {message}"
            
        # Create loan application
        loan = Loan.objects.create(
            farmer=session.farmer,
            loan_product=product,
            amount_requested=amount,
            status='PENDING'
        )
        
        return "Loan application submitted successfully. You will receive an SMS when approved."