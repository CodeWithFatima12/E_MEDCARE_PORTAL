
# Create your views here.

# def home(request):
#     return render(request, 'home.html')
from django.shortcuts import render

def signin_view(request):
    """Render the signin page"""
    return render(request, 'accounts/signin.html')

def signup_view(request):
    """Render the signup page"""
    return render(request, 'accounts/signup.html')

def homepage_view(request):
    """Render the homepage (after successful login)"""
    return render(request, 'others/homepage.html')


def pharmacy_view(request):
    """Render the pharmacy page"""
    return render(request, 'pharmacy/pharmacy.html')

def about_us_view(request):
    """Render the about us page"""
    return render(request, 'others/about-us.html')

def appointment_view(request):
    """Render the appointment page"""
    return render(request, 'appointment/appointment.html')

def ai_health_monitor_view(request):
    """Render the AI health monitor page"""
    return render(request, 'ai_module/ai_health_monitor.html')

def profile_view(request):
    """Render the profile page"""
    return render(request, 'others/dashboard.html')

def lab_reports_view(request):
    """Render the lab reports page"""
    return render(request, 'lab/lab_reports.html')

def cart_page_view(request):
    return render(request, 'pharmacy/cart.html') 