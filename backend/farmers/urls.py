from django.urls import path
from frontend.ussd.handlers import ussd_handler

urlpatterns = [
    path("ussd/", ussd_handler, name="ussd_handler"),
]