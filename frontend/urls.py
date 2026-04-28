from django.urls import path
from . import views

urlpatterns = [
    # path('', home),
    path('', views.signin_view, name='signin'),
    path('signup/', views.signup_view, name='signup'),
    path('home/', views.homepage_view, name='homepage'),
    path('pharmacy/', views.pharmacy_view, name='pharmacy'),
    path('about-us/', views.about_us_view, name='about_us'),
    path('appointment/', views.appointment_view, name='appointment'),
    path('ai-health/', views.ai_health_monitor_view, name='ai_health_monitor'),
    path('profile/', views.profile_view, name='profile'),
<<<<<<< HEAD
    path('lab-reports/',views.lab_view, name='lab_reports'),
=======
    path('lab-reports/',views.lab_reports_view, name='lab_reports'),
    path('cart/', views.cart_page_view, name='cart_view'),

>>>>>>> 33a418c9055fdf7d33b840d497a6a79ce004a7a7
]