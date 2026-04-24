# from django.urls import path
# from .views import signup_view, signin_view, SignInView, dashboard

# urlpatterns = [
#     path('signup/', signup_view, name='signup'),
#     path('signin/', signin_view, name='signin'),
#     path('dashboard/', dashboard, name='dashboard'),
# ]
from django.urls import path
from .views import signup_view, SignInView, dashboard,logout_view
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('signup/', signup_view, name='signup'),

    # ✅ Built-in Login
    path('signin/', SignInView.as_view(), name='signin'),
    # ✅ Built-in Logout
    # path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Purani line ko hata kar ye likhein:
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
]