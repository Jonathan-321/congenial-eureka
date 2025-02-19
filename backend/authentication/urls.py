from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView
from .views import UserRegistrationView, CustomTokenObtainPairView

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),
]