from django.urls import path
from . import views

urlpatterns = [
    path('lab-reports/', views.lab_view, name='lab_reports'),
    path('book-test/<int:test_id>/', views.book_appointment, name='book_appointment'),
]