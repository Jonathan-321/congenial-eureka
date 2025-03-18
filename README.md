```markdown
# AgriFinance: Agricultural Lending Platform

## Overview

AgriFinance is a comprehensive digital lending platform designed for agricultural communities in Africa.
It bridges the financial gap faced by smallholder farmers by providing accessible loans,
incorporating climate data, and enabling mobile money transactions.

## 🌱 Key Features

- **Farmer Management**: Registration, verification, and profile management for farmers
- **Loan Lifecycle Management**: Application, approval, disbursement, and repayment tracking
- **Mobile Money Integration**: Seamless MTN MoMo integration for disbursements and repayments
- **SMS Notifications**: Real-time alerts and reminders via Africa's Talking API
- **Climate-Smart Risk Assessment**: Weather and satellite data integration for better loan decisions
- **Tokenized Loans**: Vendor-specific loan tokens for agricultural inputs
- **Crop Cycle Tracking**: Monitor farming activities aligned with loan repayment schedules
- **Dynamic Credit Scoring**: Innovative scoring system using multiple data sources
- **Market Data Integration**: Crop pricing information for better planning
- **Analytics Dashboard**: Insights into loan performance and agricultural trends

## 🛠️ Technology Stack

- **Backend**: Django, Django REST Framework
- **Database**: PostgreSQL
- **Authentication**: JWT (JSON Web Tokens)
- **External APIs**:
  - MTN Mobile Money API
  - Africa's Talking SMS API
  - Weather data services
  - Satellite imagery analysis
  - Agricultural market data

## 📋 API Documentation

The API provides comprehensive endpoints for:
- User authentication (login, refresh tokens)
- Farmer registration and management
- Loan product listing and details
- Loan application, approval, and management
- Payment processing and tracking
- Vendor and tokenized loan management
- Weather and market data retrieval

Full API documentation is available in the [API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md) file.

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL
- MTN MoMo API credentials
- Africa's Talking API credentials

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/Jonathan-321/congenial-eureka.git
   cd congenial-eureka
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with the following variables:
   ```
   # Django Settings
   DEBUG=True
   SECRET_KEY=your-secret-key

   # Africa's Talking Credentials
   AT_USERNAME=sandbox
   AT_API_KEY=your-api-key

   # MTN MoMo Credentials
   MOMO_SUBSCRIPTION_KEY=your-subscription-key
   MOMO_COLLECTION_KEY=your-collection-key
   MOMO_API_USER=your-api-user
   MOMO_API_KEY=your-api-key
   MOMO_API_SECRET=your-api-secret
   MOMO_ENVIRONMENT=sandbox
   MOMO_API_URL=https://sandbox.momodeveloper.mtn.com
   ```

5. Run migrations:
   ```
   python manage.py migrate
   ```

6. Load initial data:
   ```
   python manage.py loaddata fixtures/initial_data.json
   ```

7. Start the development server:
   ```
   python manage.py runserver
   ```

## 🧪 Testing

Run the test suite:
```
pytest
```

For testing payments and SMS functionality, use the following test accounts:
- Mobile Money test number: `+250789123456`
- Africa's Talking Sandbox mode is used automatically during testing

## 📱 Mobile App Integration

The AgriFinance backend is designed to power both web and mobile applications.
Mobile apps can communicate with all API endpoints, with special consideration for:
- Token-based authentication
- Offline data synchronization
- Low-bandwidth optimized endpoints

## 🔒 Security Features

- JWT-based authentication
- Role-based permissions
- Secure credential storage
- HTTPS-only communication
- Input validation and sanitization
- Rate limiting to prevent abuse

## 🌍 Climate-Smart Agriculture

AgriFinance integrates weather data, satellite imagery, and climate risk assessments to:
- Adjust loan terms based on climate forecasts
- Provide farmers with planting advice
- Assess farm health remotely
- Calculate climate-adjusted risk scores

## 📊 Analytics and Reporting

The platform provides detailed insights including:
- Loan portfolio performance
- Repayment behavior patterns
- Climate impact on agriculture
- Regional farming trends
- Credit score distribution

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Contact

For questions or support, please contact muhirejonathan123@gmail.com (mailto:muhirejonathan123@gmail.com)
```
