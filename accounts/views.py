
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from .forms import SignupForm


# ================= LOGIN =================
class SignInView(LoginView):
    template_name = 'accounts/signin.html'

    def form_invalid(self, form):
        #  Wrong username/password
        messages.error(self.request, "Invalid username or password")
        return super().form_invalid(form)


# ================= SIGNUP =================
def signup_view(request):
    form = SignupForm()

    if request.method == 'POST':
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            # (optional success message - if you want later)
            # messages.success(request, "Account created successfully")

            return redirect('dashboard')

        else:
            #  Send all form errors to popup
            for field in form:
                for error in field.errors:
                    messages.error(request, error)

    return render(request, 'accounts/signup.html', {'form': form})


# ================= DASHBOARD =================
def dashboard(request):
    return render(request, 'others/dashboard.html')


# ==================logout===================

def logout_view(request):
    if request.method == "POST":
        logout(request)
        return render(request, 'accounts/logout.html')  # Ye aapka design wala page load karega
    
    # Agar koi direct URL browse kare to usay login par bhej dein
    return redirect('signin')