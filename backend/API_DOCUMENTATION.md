# AgriFinance API Documentation

## Overview

This document provides comprehensive documentation for the AgriFinance API, powering an agricultural finance management platform. This API enables frontend applications to manage farmers, loans, payments, and related agricultural finance services.

## Table of Contents

1. [Base URLs](#base-urls)
2. [Authentication](#authentication)
3. [Endpoints Overview](#endpoints-overview)
4. [Farmers API](#farmers-api)
5. [Loans API](#loans-api)
6. [Loan Products API](#loan-products-api)
7. [Payments API](#payments-api)
8. [Weather & Market Data API](#weather--market-data-api)
9. [Tokenization API](#tokenization-api)
10. [Crop Cycles API](#crop-cycles-api)
11. [Error Handling](#error-handling)
12. [Testing](#testing)

## Base URLs

- **Development**: `http://localhost:8000/api/`
- **Production**: `https://api.agrifinanace.com/api/`

## Authentication

All API endpoints (except for authentication endpoints) require JWT authentication.

### Obtaining Access Tokens

**Endpoint**: `POST /api/auth/token/`

**Request Body**:
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Using the Access Token

Include the access token in the Authorization header of all requests:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### Refreshing Tokens

When the access token expires, use the refresh token to obtain a new one:

**Endpoint**: `POST /api/auth/token/refresh/`

**Request Body**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### User Registration

**Endpoint**: `POST /api/auth/register/`

**Request Body**:
```json
{
  "username": "new_farmer",
  "password": "secure_password",
  "email": "farmer@example.com",
  "phone_number": "+250789123456",
  "role": "FARMER"
}
```

## Endpoints Overview

| Resource | Endpoints |
|----------|-----------|
| Authentication | `/api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/register/` |
| Farmers | `/api/farmers/`, `/api/farmers/{id}/` |
| Loans | `/api/loans/`, `/api/loans/{id}/`, `/api/loans/{id}/apply/`, `/api/loans/{id}/approve/`, `/api/loans/{id}/disburse/`, `/api/loans/status/{id}/` |
| Loan Products | `/api/loans/products/`, `/api/loans/products/{id}/` |
| Payments | `/api/payments/`, `/api/loans/{id}/payments/` |
| Weather & Market | `/api/loans/weather/forecast/{location}/`, `/api/loans/market/prices/{crop_type}/` |
| Crop Cycles | `/api/loans/crop-cycles/`, `/api/loans/harvest-schedule/{loan_id}/` |
| Dashboards | `/api/loans/farmer/{farmer_id}/dashboard/` |

## Farmers API

### List Farmers

**Endpoint**: `GET /api/farmers/`

**Query Parameters**:
- `location` (optional): Filter by farmer location
- `page` (optional): Page number for pagination
- `page_size` (optional): Items per page

**Response**:
```json
{
  "count": 15,
  "next": "http://api.example.com/api/farmers/?page=2",
  "previous": null,
  "results": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "user": {
        "id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
        "username": "farmer1"
      },
      "name": "John Doe",
      "phone_number": "+250789123456",
      "location": "Kigali",
      "farm_size": 2.5,
      "created_at": "2023-01-15T12:00:00Z",
      "credit_score": 750
    },
    // More farmers...
  ]
}
```

### Get Farmer Profile

**Endpoint**: `GET /api/farmers/{id}/`

**Response**:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "user": {
    "id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
    "username": "farmer1"
  },
  "name": "John Doe",
  "phone_number": "+250789123456",
  "location": "Kigali",
  "farm_size": 2.5,
  "created_at": "2023-01-15T12:00:00Z",
  "credit_score": 750,
  "loan_summary": {
    "active_loans": 1,
    "total_borrowed": "5000.00",
    "total_repaid": "2000.00"
  }
}
```

### Create Farmer Profile

**Endpoint**: `POST /api/farmers/`

**Request Body**:
```json
{
  "name": "Jane Smith",
  "phone_number": "+250789123457",
  "location": "Musanze",
  "farm_size": 3.2
}
```

**Response**:
```json
{
  "id": "5fa85f64-5717-4562-b3fc-2c963f66afa8",
  "name": "Jane Smith",
  "phone_number": "+250789123457",
  "location": "Musanze",
  "farm_size": 3.2,
  "created_at": "2023-05-20T14:30:00Z",
  "credit_score": 0
}
```

### Update Farmer Profile

**Endpoint**: `PUT /api/farmers/{id}/`

**Request Body**:
```json
{
  "location": "Rwamagana",
  "farm_size": 4.0
}
```

## Loans API

### List Loans

**Endpoint**: `GET /api/loans/`

**Query Parameters**:
- `status` (optional): Filter by loan status (e.g., PENDING, APPROVED, ACTIVE)
- `farmer_id` (optional): Filter by farmer ID
- `page` (optional): Page number for pagination

**Response**:
```json
{
  "count": 25,
  "next": "http://api.example.com/api/loans/?page=2",
  "previous": null,
  "results": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "farmer": {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "John Doe"
      },
      "loan_product": {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "Seed Loan"
      },
      "amount_requested": "500.00",
      "amount_approved": "500.00",
      "status": "ACTIVE",
      "application_date": "2023-01-15T12:00:00Z",
      "due_date": "2023-04-15T12:00:00Z"
    },
    // More loans...
  ]
}
```

### Get Loan Details

**Endpoint**: `GET /api/loans/{id}/`

**Response**:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "farmer": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "John Doe",
    "phone_number": "+250789123456"
  },
  "loan_product": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Seed Loan",
    "interest_rate": "10.00",
    "duration_days": 90
  },
  "amount_requested": "500.00",
  "amount_approved": "500.00",
  "status": "ACTIVE",
  "application_date": "2023-01-15T12:00:00Z",
  "approval_date": "2023-01-16T12:00:00Z",
  "disbursement_date": "2023-01-17T12:00:00Z",
  "due_date": "2023-04-15T12:00:00Z",
  "payment_schedules": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "due_date": "2023-02-15T12:00:00Z",
      "amount": "175.00",
      "status": "PAID"
    },
    {
      "id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
      "due_date": "2023-03-15T12:00:00Z",
      "amount": "175.00", 
      "status": "PENDING"
    },
    {
      "id": "5fa85f64-5717-4562-b3fc-2c963f66afa8",
      "due_date": "2023-04-15T12:00:00Z",
      "amount": "175.00",
      "status": "PENDING"
    }
  ],
  "transactions": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "transaction_type": "DISBURSEMENT",
      "amount": "500.00",
      "status": "COMPLETED",
      "created_at": "2023-01-17T12:00:00Z"
    },
    {
      "id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
      "transaction_type": "REPAYMENT",
      "amount": "175.00",
      "status": "COMPLETED", 
      "created_at": "2023-02-15T10:00:00Z"
    }
  ]
}
```

### Apply for Loan

**Endpoint**: `POST /api/loans/{loan_product_id}/apply/`

**Request Body**:
```json
{
  "amount": "500.00"
}
```

**Response**:
```json
{
  "status": "PENDING",
  "loan_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message": "Your loan application has been submitted successfully"
}
```

### Approve Loan

**Endpoint**: `POST /api/loans/{id}/approve/`

**Request Body**:
```json
{
  "amount_approved": "450.00",
  "notes": "Approved with reduced amount based on credit score"
}
```

**Response**:
```json
{
  "status": "APPROVED",
  "loan_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message": "Loan has been approved"
}
```

### Disburse Loan

**Endpoint**: `POST /api/loans/{id}/disburse/`

**Response**:
```json
{
  "status": "DISBURSED",
  "loan_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "transaction_id": "6fa85f64-5717-4562-b3fc-2c963f66afa9",
  "message": "Loan disbursement initiated"
}
```

### Get Loan Status

**Endpoint**: `GET /api/loans/status/{loan_id}/`

**Response**:
```json
{
  "loan_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "ACTIVE",
  "amount_disbursed": "450.00",
  "amount_due": "350.00",
  "amount_paid": "175.00",
  "next_payment_date": "2023-03-15T12:00:00Z",
  "next_payment_amount": "175.00",
  "days_to_next_payment": 15
}
```

### Farmer Dashboard

**Endpoint**: `GET /api/loans/farmer/{farmer_id}/dashboard/`

**Response**:
```json
{
  "total_loans": 3,
  "active_loans": 1,
  "total_approved": "5000.00",
  "total_repaid": "2000.00",
  "upcoming_payments": 2,
  "overdue_payments": 0,
  "credit_score": 750,
  "recent_loans": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "status": "ACTIVE",
      "amount_approved": "500.00",
      "due_date": "2023-04-15T12:00:00Z"
    }
  ]
}
```

## Loan Products API

### List Loan Products

**Endpoint**: `GET /api/loans/products/`

**Response**:
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Seed Loan",
      "description": "Short-term loan for purchasing seeds",
      "min_amount": "100.00",
      "max_amount": "1000.00",
      "interest_rate": "10.00",
      "duration_days": 90,
      "repayment_schedule_type": "FIXED",
      "is_active": true
    },
    // More loan products...
  ]
}
```

### Get Loan Product Details

**Endpoint**: `GET /api/loans/products/{id}/`

**Response**:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Seed Loan",
  "description": "Short-term loan for purchasing seeds",
  "min_amount": "100.00",
  "max_amount": "1000.00",
  "interest_rate": "10.00",
  "duration_days": 90,
  "repayment_schedule_type": "FIXED",
  "is_active": true,
  "requirements": {
    "credit_score": 700,
    "minimum_farm_size": 1.0
  }
}
```

## Payments API

### Make Payment

**Endpoint**: `POST /api/payments/`

**Request Body**:
```json
{
  "loan_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "amount": "175.00",
  "phone_number": "+250789123456"
}
```

**Response**:
```json
{
  "transaction_id": "7fa85f64-5717-4562-b3fc-2c963f66afa0",
  "status": "PENDING",
  "message": "Payment request initiated. Please confirm on your mobile device."
}
```

### Get Payment History

**Endpoint**: `GET /api/loans/{id}/payments/`

**Response**:
```json
{
  "loan_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "total_paid": "175.00",
  "outstanding_balance": "350.00",
  "transactions": [
    {
      "id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
      "transaction_type": "REPAYMENT",
      "amount": "175.00",
      "status": "COMPLETED",
      "created_at": "2023-02-15T10:00:00Z",
      "reference": "TXN123456789"
    }
  ]
}
```

### MoMo Webhook

**Endpoint**: `POST /api/loans/webhooks/momo/`

This endpoint handles callbacks from the mobile money provider when payments are processed.

## Weather & Market Data API

### Get Weather Forecast

**Endpoint**: `GET /api/loans/weather/forecast/{location}/`

**Response**:
```json
{
  "location": "Kigali",
  "current": {
    "temperature": 24,
    "conditions": "Partly Cloudy",
    "humidity": 65
  },
  "forecast": [
    {
      "date": "2023-05-21",
      "min_temp": 18,
      "max_temp": 26,
      "conditions": "Sunny",
      "precipitation_chance": 10
    },
    // More forecast days...
  ],
  "alerts": [],
  "farming_recommendations": [
    "Good conditions for planting maize in the next 3 days",
    "Consider irrigation for vegetable crops due to low rainfall forecast"
  ]
}
```

### Get Market Prices

**Endpoint**: `GET /api/loans/market/prices/{crop_type}/`

**Response**:
```json
{
  "crop_type": "maize",
  "unit": "kg",
  "current_price": "0.35",
  "price_trend": [
    {
      "date": "2023-04-01",
      "price": "0.32"
    },
    {
      "date": "2023-04-15",
      "price": "0.33"
    },
    {
      "date": "2023-05-01",
      "price": "0.34"
    },
    {
      "date": "2023-05-15",
      "price": "0.35"
    }
  ],
  "forecast": {
    "next_month": "0.36",
    "trend": "RISING",
    "confidence": "MEDIUM"
  }
}
```

## Tokenization API

For loans that utilize tokenized disbursements for approved vendors only.

### Validate Token

**Endpoint**: `POST /api/loans/tokens/validate/`

**Request Body**:
```json
{
  "token_code": "ABC123XYZ",
  "vendor_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "amount": "200.00"
}
```

**Response**:
```json
{
  "is_valid": true,
  "token_id": "8fa85f64-5717-4562-b3fc-2c963f66afa1",
  "available_balance": "300.00",
  "message": "Token is valid"
}
```

## Crop Cycles API

### List Crop Cycles

**Endpoint**: `GET /api/loans/crop-cycles/`

**Response**:
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "9fa85f64-5717-4562-b3fc-2c963f66afa2",
      "farmer": {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "John Doe"
      },
      "crop_type": "maize",
      "planting_date": "2023-03-01T00:00:00Z",
      "expected_harvest_date": "2023-06-15T00:00:00Z",
      "expected_yield": "2000.00",
      "farm_size": "1.5",
      "status": "GROWING"
    },
    // More crop cycles...
  ]
}
```

### Get Harvest Schedule

**Endpoint**: `GET /api/loans/harvest-schedule/{loan_id}/`

**Response**:
```json
{
  "loan_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "crop_cycles": [
    {
      "id": "9fa85f64-5717-4562-b3fc-2c963f66afa2",
      "crop_type": "maize",
      "expected_harvest_date": "2023-06-15T00:00:00Z",
      "expected_yield": "2000.00",
      "expected_revenue": "700.00"
    }
  ],
  "payment_schedule": [
    {
      "id": "5fa85f64-5717-4562-b3fc-2c963f66afa8",
      "due_date": "2023-06-20T12:00:00Z",
      "amount": "350.00",
      "status": "PENDING"
    }
  ],
  "weather_risk": "LOW",
  "market_forecast": "STABLE"
}
```

## Error Handling

The API returns standard HTTP status codes:

- **200 OK**: Request succeeded
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid input data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Server Error**: Internal server error

Error responses follow this format:

```json
{
  "error": "Error summary",
  "detail": "Detailed explanation of what went wrong"
}
```

## Testing

### API Documentation Tools

You can access the interactive API documentation at:

- **Swagger UI**: `/api/docs/`
- **ReDoc**: `/api/redoc/`
- **OpenAPI Schema**: `/api/schema/`

### Testing Mobile Money Integration

For testing payments and disbursements, use the following test phone numbers:

- `+250789123456`: Always successful
- `+250789123457`: Payment pending then success
- `+250789123458`: Payment pending then failure

### Testing SMS Integration

For testing SMS notifications:

- All SMS will be sent via Africa's Talking Sandbox when in development mode
- Check the console logs for SMS content in test mode
