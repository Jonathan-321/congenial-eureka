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
- **Crop Cycle Tracking**: Monitor farming activities aligned with loan repayment schedule
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
  - OpenWeatherMap API
  - Sentinel Hub Satellite Data API
  - Agricultural market data

## 📋 API Documentation

The API provides comprehensive endpoints for:
- User authentication (login, refresh tokens)
- Farmer registration and management
- Loan product listing and details
- Loan application, approval, and management
- Payment processing and tracking
- Vendor and tokenized loan management
- Weather and satellite data retrieval

Full API documentation is available in the [API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md) file.

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL
- MTN MoMo API credentials
- Africa's Talking API credentials
- OpenWeatherMap API key
- Sentinel Hub API credentials (for satellite data)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/agrifinance.git
   cd agrifinance
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

   # Database
   DATABASE_URL=postgres://user:password@localhost:5432/agrifinance

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
   
   # OpenWeatherMap API for climate data
   OPENWEATHER_API_KEY=your-openweather-api-key
   
   # Sentinel Hub API for satellite imagery
   SENTINEL_INSTANCE_ID=your-sentinel-instance-id
   SENTINEL_API_KEY=your-sentinel-api-key
   SENTINEL_OAUTH_CLIENT_ID=your-sentinel-oauth-client-id
   SENTINEL_OAUTH_CLIENT_SECRET=your-sentinel-oauth-client-secret
   ```

5. Run migrations:
   ```
   python manage.py migrate
   ```

6. Run the django server:
   ```
   python manage.py runserver
   ```

## 📱 Mobile Access

Farmers can access the platform through:

- **USSD Interface**: Dial the USSD code to access services
- **SMS Notifications**: Receive updates and alerts
- **Mobile Money**: Make payments using MTN Mobile Money

## 🧪 Testing

Run the test suite:
```
pytest
```

## 🌍 Climate-Smart Agriculture Enhancement

AgriFinance now integrates advanced satellite and weather data to:
- Calculate NDVI (Normalized Difference Vegetation Index) for farm health assessment
- Track rainfall anomalies compared to historical patterns
- Provide farmers with climate-specific crop recommendations
- Adjust loan terms automatically based on adverse weather conditions
- Generate region-specific risk profiles for better lending decisions

## 📊 New Management Commands

The platform includes new management commands to work with climate data:

1. Update farmer coordinates:
   ```
   python manage.py update_farmer_coordinates [--all] [--farmer_id=ID]
   ```

2. Update climate data (NDVI, rainfall anomalies):
   ```
   python manage.py update_climate_data [--force] [--farmer_id=ID]
   ```

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

For questions or support, please contact [muhirejonathan123@gmail.com](mailto:muhirejonathan123@gmail.com) 
