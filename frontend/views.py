
# Create your views here.

# def home(request):
#     return render(request, 'home.html')
# from django.shortcuts import render
import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

@login_required
def profile_view(request):

    # ✅ Superuser / staff admin panel
    if request.user.is_superuser or request.user.is_staff:
        return redirect('/admin/')

    # ⏰ Greeting logic
    hour = datetime.datetime.now().hour

    if hour < 12:
        greet = "Good Morning"
    elif hour < 18:
        greet = "Good Afternoon"
    else:
        greet = "Good Evening"

    user = request.user
    role = user.role

    # 👇 shared context (important)
    context = {
        'greet': greet,
        'name': user.get_full_name() if user.get_full_name() else user.username,
        'email': user.email,
        'role': role
    }

    # 👇 role-based dashboards
    if role == 'doctor':
        return render(request, 'appointment/doctor_dashboard.html', context)

    elif role == 'patient':
        return render(request, 'appointment/patient_dashboard.html', context)

    elif role == 'user':
        return render(request, 'others/dashboard.html', context)

    else:
        return render(request, 'others/homepage.html')
    
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

# def profile_view(request):
#     """Render the profile page"""
#     return render(request, 'others/dashboard.html')

def lab_reports_view(request):
    """Render the lab reports page"""
    return render(request, 'lab/lab_reports.html')

def cart_page_view(request):
    return render(request, 'pharmacy/cart.html') 