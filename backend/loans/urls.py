from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, ussd_views
from .views import CropCycleViewSet, LoanViewSet, LoanProductViewSet

# Create router for REST API endpoints
router = DefaultRouter()
router.register(r'', views.LoanViewSet, basename='loan')
router.register(r'products', LoanProductViewSet, basename='loan-products')
router.register(r'crop-cycles', CropCycleViewSet, basename='crop-cycles')

# API endpoints
urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
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

     path('', LoanViewSet.as_view({'get': 'list', 'post': 'create'}), name='loan-list'),
     # Add this if it's missing
     path('products/', LoanProductViewSet.as_view({'get': 'list'}), name='loan-product-list'),
    
    # Custom action URLs - make sure they go to the correct viewset method
    path('<int:pk>/apply/', LoanViewSet.as_view({'post': 'apply'}), name='loan-apply'),
    path('<int:pk>/approve/', LoanViewSet.as_view({'post': 'approve'}), name='loan-approve'),
    path('<int:pk>/disburse/', LoanViewSet.as_view({'post': 'disburse'}), name='loan-disburse'),
    path('webhooks/momo/', views.momo_webhook, name='momo-webhook'),
]