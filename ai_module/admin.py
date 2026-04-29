from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import HealthMetric

@admin.register(HealthMetric)
class HealthMetricAdmin(admin.ModelAdmin):
    # This list defines which columns show up in the admin table
    list_display = ('user', 'glucose_level', 'bmi', 'hba1c', 'created_at')
    
    # Optional: Adds a filter sidebar so you can filter by date or user
    list_filter = ('created_at', 'user')
    
    # Optional: Adds a search bar to search by username
    search_fields = ('user__username', 'glucose_level')
    
    # Optional: Makes the list sorted by the latest entry by default
    ordering = ('-created_at',)