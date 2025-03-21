from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, ussd_views
from .views import CropCycleViewSet, LoanViewSet, LoanProductViewSet,api_root

# Create router for REST API endpoints
router = DefaultRouter()
router.register(r'products', LoanProductViewSet, basename='loan-product')
router.register(r'loans', LoanViewSet, basename='loan')
router.register(r'crop-cycles', CropCycleViewSet, basename='crop-cycles')

# API endpoints
urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    path('', api_root, name='loans-api-root'),
    path('ussd/callback/', ussd_views.ussd_callback, name='ussd_callback'),

    path('farmer/<uuid:farmer_id>/dashboard/', 
         views.FarmerDashboardAPIView.as_view(), 
         name='farmer-dashboard'),
    path('status/<uuid:loan_id>/', 
         views.LoanStatusAPIView.as_view(), 
         name='loan-status'),
    path('tokens/validate/', 
         views.TokenValidationView.as_view(), 
         name='token-validation'),
    
    path('harvest-schedule/<uuid:loan_id>/', 
         views.HarvestScheduleAPIView.as_view(), 
         name='harvest-schedule'),
    path('weather/forecast/<str:location>/', 
         views.WeatherForecastAPIView.as_view(), 
         name='weather-forecast'),
    path('market/prices/<str:crop_type>/', 
         views.MarketPricesAPIView.as_view(), 
         name='market-prices'),
    
    # Custom action URLs - properly namespaced
    path('loans/<int:pk>/apply/', LoanViewSet.as_view({'post': 'apply'}), name='loan-apply'),
    path('loans/<int:pk>/approve/', LoanViewSet.as_view({'post': 'approve'}), name='loan-approve'),
    path('loans/<int:pk>/disburse/', LoanViewSet.as_view({'post': 'disburse'}), name='loan-disburse'),
    path('webhooks/momo/', views.momo_webhook, name='momo-webhook'),
]