from django.urls import path
from .views import DepartmentListView

urlpatterns = [
    # Full URL: /api/appointment/departments/
    path('departments/', DepartmentListView.as_view(), name='dept-api'),
]