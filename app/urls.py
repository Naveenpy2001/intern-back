from django.urls import path
from . import views

urlpatterns = [
    
    path('check-registration-status/<str:email>/', views.check_registration_status, name='check_registration_status'),
    path('register/', views.register, name='register'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('get-user-details/<str:email>/', views.get_user_details, name='get_user_details'),
    path('generate-certificate/<str:email>/', views.generate_certificate, name='generate_certificate'),

    path('register_user/', views.RegisterUserView.as_view(), name='register_user'),

]
